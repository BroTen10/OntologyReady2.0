import { useEffect, useRef, useState, useCallback } from 'react';
import { Graph } from '@antv/g6';
import { Button, Input, Select, Slider, Space, Tabs, Tag, Tooltip, Typography, message } from 'antd';
import {
  ZoomInOutlined, ZoomOutOutlined, ExpandOutlined, AimOutlined,
  SearchOutlined, CloseOutlined,
  DownloadOutlined, FullscreenOutlined, FullscreenExitOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;

const LAYOUT_OPTIONS = [
  { value: 'force', label: '力导向' },
  { value: 'dagre', label: '层次化' },
  { value: 'radial', label: '径向' },
  { value: 'circular', label: '圆形' },
  { value: 'grid', label: '网格' },
  { value: 'concentric', label: '同心圆' },
];

export default function GraphPage() {
  const containerRef = useRef(null);
  const graphRef = useRef(null);
  const [mode, setMode] = useState('light');
  const [layout, setLayout] = useState('force');
  const [depth, setDepth] = useState(1);
  const [stats, setStats] = useState({ nodeCount: 0, edgeCount: 0 });
  const [selectedNode, setSelectedNode] = useState(null);
  const [searchText, setSearchText] = useState('');
  const [fullscreen, setFullscreen] = useState(false);
  const [dataset] = useState('_ontology_default');

  const toggleTheme = () => setMode((m) => (m === 'light' ? 'dark' : 'light'));
  const isLight = mode === 'light';

  const initGraph = useCallback(() => {
    if (!containerRef.current) return;
    if (graphRef.current) { try { graphRef.current.destroy(); } catch {} graphRef.current = null; }

    try {
      const container = containerRef.current;
      const graph = new Graph({
        container,
        width: container.clientWidth || 800,
        height: container.clientHeight || 500,
        autoFit: 'view',
        animation: true,
        background: isLight ? '#f8f9fc' : '#0f172a',
        layout: { type: layout },
        data: { nodes: [], edges: [] },
        node: {
          type: 'circle',
          style: {
            size: 36,
            fill: isLight ? '#7c3aed' : '#38bdf8',
            stroke: isLight ? '#e4e7ed' : '#334155',
            lineWidth: 2,
            labelText: '',
            labelFontSize: 12,
            labelFill: isLight ? '#334155' : '#e2e8f0',
            labelOffsetY: 8,
          },
        },
        edge: {
          type: 'line',
          style: {
            stroke: isLight ? '#c0c4cc' : '#475569',
            lineWidth: 1.5,
            endArrow: true,
            labelText: '',
            labelFontSize: 10,
            labelFill: isLight ? '#94a3b8' : '#64748b',
          },
        },
        behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element', 'hover-activate'],
      });

      graph.on('node:click', (evt) => {
        setSelectedNode(evt.target?.id ? { id: evt.target.id, data: evt.target } : null);
      });
      graph.on('canvas:click', () => setSelectedNode(null));

      graphRef.current = graph;
    } catch (e) {
      console.error('G6 init error:', e);
    }
  }, [layout, isLight]);

  useEffect(() => {
    initGraph();
    return () => { if (graphRef.current) { try { graphRef.current.destroy(); } catch {} graphRef.current = null; } };
  }, [initGraph]);

  const loadData = useCallback(async () => {
    if (!graphRef.current) return;
    try {
      const { data: statsData } = await fetch(`/api/datasets/${dataset}/ontology/graph/stats`).then((r) => r.json());
      if (statsData?.code === 0) setStats({ nodeCount: statsData.data.node_count || 0, edgeCount: statsData.data.edge_count || 0 });

      const objRes = await fetch(`/api/datasets/${dataset}/ontology/objects?page_size=500`).then((r) => r.json());
      const objs = objRes?.data?.items || [];
      const nodes = objs.map((o) => ({
        id: String(o.object_id),
        data: { ...o.properties, _item: o },
        style: { labelText: String(o.properties?.ygxm || o.properties?.name || o.object_id) },
      }));

      const linkRes = await fetch(`/api/datasets/${dataset}/ontology/links?page_size=500`).then((r) => r.json());
      const linksList = linkRes?.data?.items || [];
      const edges = linksList.map((l) => ({
        id: String(l.link_id),
        source: String(l.source_id),
        target: String(l.target_id),
        data: { _item: l },
        style: { labelText: String(l.link_type || '') },
      }));

      if (graphRef.current) {
        graphRef.current.setData({ nodes, edges });
        await graphRef.current.render();
        graphRef.current.fitView();
        setStats({ nodeCount: nodes.length, edgeCount: edges.length });
      }
    } catch { /* no data yet */ }
  }, [dataset]);

  useEffect(() => { loadData(); }, [loadData]);

  const expandNeighbors = async () => {
    if (!selectedNode || !graphRef.current) return;
    try {
      const item = selectedNode.data?._item || selectedNode.data || {};
      const objType = item.object_type || 'Object';
      const res = await fetch(`/api/datasets/${dataset}/ontology/graph/neighbors/${objType}/${selectedNode.id}?depth=${depth}`).then((r) => r.json());
      const ns = res?.data?.nodes || [];
      const es = res?.data?.edges || [];

      const existing = graphRef.current.getData();
      const nodeIds = new Set((existing.nodes || []).map((n) => String(n.id)));
      const edgeIds = new Set((existing.edges || []).map((e) => String(e.id)));

      const newNodes = ns.filter((n) => !nodeIds.has(String(n.object_id))).map((n) => ({
        id: String(n.object_id),
        data: { ...n.properties, _item: n },
        style: { labelText: String(n.properties?.ygxm || n.properties?.name || n.object_id) },
      }));
      const newEdges = es.filter((e) => !edgeIds.has(String(e.link_id))).map((e) => ({
        id: String(e.link_id),
        source: String(e.source_id),
        target: String(e.target_id),
        data: { _item: e },
        style: { labelText: String(e.link_type || '') },
      }));

      graphRef.current.addData({ nodes: newNodes, edges: newEdges });
      await graphRef.current.render();
      setStats((s) => ({ nodeCount: s.nodeCount + newNodes.length, edgeCount: s.edgeCount + newEdges.length }));
      message.success(`展开 ${newNodes.length} 个节点，${newEdges.length} 条边`);
    } catch { message.error('展开失败'); }
  };

  const changeLayout = (lt) => {
    setLayout(lt);
    if (graphRef.current) {
      graphRef.current.setLayout({ type: lt });
      graphRef.current.layout().then(() => graphRef.current.fitView());
    }
  };

  const handleZoom = (delta) => {
    if (graphRef.current) {
      const z = graphRef.current.getZoom();
      graphRef.current.zoomTo(z + delta);
    }
  };

  const handleSearch = () => {
    if (graphRef.current && searchText) {
      try {
        graphRef.current.focusElement(searchText);
      } catch { message.info('节点未找到'); }
    }
  };

  const nodeProps = selectedNode?.data?._item?.properties || selectedNode?.data || {};

  return (
    <div ref={(el) => { if (el && fullscreen) el.requestFullscreen?.().catch(() => {}); }} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: '#fff', borderBottom: '1px solid #e8e8e8', flexWrap: 'wrap', gap: 8 }}>
        <Space>
          <Tabs size="small" activeKey="entity" items={[{ key: 'entity', label: '实体图谱' }, { key: 'structure', label: '结构图谱' }]} />
          <Select size="small" value={layout} onChange={changeLayout} style={{ width: 100 }} options={LAYOUT_OPTIONS} />
        </Space>
        <Space>
          <Input size="small" prefix={<SearchOutlined />} placeholder="搜索节点..." value={searchText}
            onChange={(e) => setSearchText(e.target.value)} style={{ width: 160 }} onPressEnter={handleSearch} />
          <Tooltip title={isLight ? '深色主题' : '浅色主题'}>
            <Button size="small" type={isLight ? 'primary' : 'default'} onClick={toggleTheme}>主题</Button>
          </Tooltip>
          <Tooltip title="适应画布"><Button size="small" icon={<AimOutlined />} onClick={() => graphRef.current?.fitView()} /></Tooltip>
          <Tooltip title="放大"><Button size="small" icon={<ZoomInOutlined />} onClick={() => handleZoom(0.2)} /></Tooltip>
          <Tooltip title="缩小"><Button size="small" icon={<ZoomOutOutlined />} onClick={() => handleZoom(-0.2)} /></Tooltip>
          <Tooltip title="导出"><Button size="small" icon={<DownloadOutlined />} onClick={() => graphRef.current?.toDataURL().then((url) => { const a = document.createElement('a'); a.href = url; a.download = 'graph.png'; a.click(); }).catch(() => {})} /></Tooltip>
          <Tooltip title="全屏"><Button size="small" icon={fullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />} onClick={() => setFullscreen(!fullscreen)} /></Tooltip>
        </Space>
      </div>

      <div style={{ flex: 1, display: 'flex', position: 'relative' }}>
        <div ref={containerRef} style={{ flex: 1, minHeight: 500 }} />

        {selectedNode && (
          <div style={{ background: '#fff', borderLeft: '1px solid #e8e8e8', padding: 16, overflow: 'auto', flexShrink: 0, width: window.innerWidth < 900 ? 320 : 280 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <Title level={5} style={{ margin: 0 }}>节点详情</Title>
              <Button size="small" type="text" icon={<CloseOutlined />} onClick={() => setSelectedNode(null)} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text strong>ID: </Text><Text code>{selectedNode.id}</Text>
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text strong>类型: </Text>
              <Tag color="purple">{selectedNode.data?._item?.object_type || 'Unknown'}</Tag>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>属性</Text>
              <div style={{ background: '#f8f9fc', borderRadius: 6, padding: 8, marginTop: 4, maxHeight: 200, overflow: 'auto' }}>
                {Object.entries(nodeProps).filter(([k]) => !k.startsWith('_') && k !== 'object_type').map(([k, v]) => (
                  <div key={k} style={{ fontSize: 12, lineHeight: '20px' }}>
                    <Text type="secondary">{k}: </Text><Text>{String(v)}</Text>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text strong>展开深度: </Text>
              <Slider min={1} max={5} value={depth} onChange={setDepth} />
            </div>
            <Button type="primary" icon={<ExpandOutlined />} block onClick={expandNeighbors}>展开邻居</Button>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 16px', background: '#fafbfc', borderTop: '1px solid #e8e8e8' }}>
        <Space size="large">
          <Text type="secondary">节点: <Text strong>{stats.nodeCount}</Text></Text>
          <Text type="secondary">边: <Text strong>{stats.edgeCount}</Text></Text>
          <Text type="secondary">布局: <Tag>{LAYOUT_OPTIONS.find((o) => o.value === layout)?.label}</Tag></Text>
        </Space>
        <Text type="secondary">AntV G6 5.x</Text>
      </div>
    </div>
  );
}
