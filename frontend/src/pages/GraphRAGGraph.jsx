import { useEffect, useRef, useState, useCallback } from 'react';
import { Graph } from '@antv/g6';
import {
  Button, Input, Select, Slider, Space, Tag, Tooltip, Typography, message,
  Card, Collapse, Badge, Empty,
} from 'antd';
import {
  ZoomInOutlined, ZoomOutOutlined, ExpandOutlined, AimOutlined,
  SearchOutlined, CloseOutlined, DownloadOutlined,
  FullscreenOutlined, FullscreenExitOutlined, FilterOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';
import * as graphragApi from '../api/graphrag';

const { Text, Title } = Typography;

const ENTITY_COLORS = {
  organization: '#7c3aed',
  person: '#3b82f6',
  geo: '#10b981',
  event: '#f59e0b',
  category: '#ec4899',
};

const LAYOUT_OPTIONS = [
  { value: 'force', label: '力导向' },
  { value: 'dagre', label: '层次化' },
  { value: 'radial', label: '径向' },
  { value: 'circular', label: '圆形' },
  { value: 'grid', label: '网格' },
  { value: 'concentric', label: '同心圆' },
];

export default function GraphRAGGraph() {
  const [searchParams] = useSearchParams();
  const wsId = searchParams.get('ws') || '';
  const containerRef = useRef(null);
  const graphRef = useRef(null);
  const [layout, setLayout] = useState('force');
  const [depth, setDepth] = useState(1);
  const [stats, setStats] = useState({ entity_count: 0, relation_count: 0 });
  const [selectedNode, setSelectedNode] = useState(null);
  const [searchText, setSearchText] = useState('');
  const [fullscreen, setFullscreen] = useState(false);
  const [filterType, setFilterType] = useState(null);
  const [workspace, setWorkspace] = useState(null);
  const [loading, setLoading] = useState(false);

  const entityColors = ENTITY_COLORS;

  const loadWorkspace = useCallback(async () => {
    if (!wsId) return;
    try {
      const res = await graphragApi.getWorkspace(wsId);
      if (res.code === 0) setWorkspace(res.data);
    } catch { /* */ }
  }, [wsId]);

  useEffect(() => { loadWorkspace(); }, [loadWorkspace]);

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
        background: '#f8f9fc',
        layout: { type: layout },
        data: { nodes: [], edges: [] },
        node: {
          type: 'circle',
          style: (d) => ({
            size: 40,
            fill: entityColors[d.data?.entity_type] || '#7c3aed',
            stroke: '#e4e7ed',
            lineWidth: 2,
            labelText: d.data?.label || d.id,
            labelFontSize: 12,
            labelFill: '#334155',
            labelOffsetY: 8,
          }),
          state: {
            active: { lineWidth: 4, stroke: '#f59e0b', shadowBlur: 10, shadowColor: '#f59e0b' },
            inactive: { opacity: 0.3 },
          },
        },
        edge: {
          type: 'line',
          style: {
            stroke: '#c0c4cc',
            lineWidth: 1.5,
            endArrow: true,
            labelText: (d) => d.data?.label || '',
            labelFontSize: 10,
            labelFill: '#94a3b8',
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
  }, [layout]);

  useEffect(() => {
    initGraph();
    return () => { if (graphRef.current) { try { graphRef.current.destroy(); } catch {} graphRef.current = null; } };
  }, [initGraph]);

  const loadData = useCallback(async () => {
    if (!graphRef.current || !wsId) return;
    setLoading(true);
    try {
      const res = await graphragApi.getGraph(wsId);
      if (res.code !== 0) { setLoading(false); return; }

      const data = res.data || {};
      const nodes = (data.nodes || []).map((n) => ({
        id: n.id,
        data: {
          label: n.label,
          entity_type: n.entity_type,
          description: n.description,
          properties: n.properties,
        },
      }));
      const edges = (data.edges || []).map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        data: { label: e.label, source_name: e.source_name, target_name: e.target_name },
      }));

      let filteredNodes = nodes;
      if (filterType) {
        const matchingIds = new Set(nodes.filter((n) => n.data.entity_type === filterType).map((n) => n.id));
        filteredNodes = nodes.filter((n) => matchingIds.has(n.id));
        const filteredEdges = edges.filter((e) => matchingIds.has(e.source) && matchingIds.has(e.target));
        graphRef.current.setData({ nodes: filteredNodes, edges: filteredEdges });
      } else {
        graphRef.current.setData({ nodes, edges });
      }

      await graphRef.current.render();
      graphRef.current.fitView();
      setStats(data.stats || { entity_count: nodes.length, relation_count: edges.length });
    } catch { message.error('加载图谱数据失败'); }
    finally { setLoading(false); }
  }, [wsId, filterType]);

  useEffect(() => { loadData(); }, [loadData]);

  const expandNeighbors = async () => {
    if (!selectedNode || !graphRef.current) return;
    try {
      const res = await graphragApi.getNeighbors(wsId, selectedNode.id, depth);
      if (res.code !== 0) return;
      const ns = res.data?.nodes || [];
      const es = res.data?.edges || [];

      const existing = graphRef.current.getData();
      const nodeIds = new Set((existing.nodes || []).map((n) => String(n.id)));
      const edgeIds = new Set((existing.edges || []).map((e) => String(e.id)));

      const newNodes = [];
      for (const n of ns) {
        const nid = String(n.id);
        if (!nodeIds.has(nid)) {
          nodeIds.add(nid);
          newNodes.push({
            id: nid,
            data: { label: n.label, entity_type: n.entity_type, description: n.description },
          });
        }
      }
      const newEdges = [];
      for (const e of es) {
        const eid = String(e.id);
        if (!edgeIds.has(eid)) {
          edgeIds.add(eid);
          newEdges.push({ id: eid, source: String(e.source), target: String(e.target), data: { label: e.label } });
        }
      }

      graphRef.current.addData({ nodes: newNodes, edges: newEdges });
      await graphRef.current.render();
      setStats((s) => ({ ...s, entity_count: s.entity_count + newNodes.length, relation_count: s.relation_count + newEdges.length }));
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
      graphRef.current.zoomTo(graphRef.current.getZoom() + delta);
    }
  };

  const handleSearch = () => {
    if (graphRef.current && searchText) {
      try { graphRef.current.focusElement(searchText); } catch { message.info('节点未找到'); }
    }
  };

  const handleFilterChange = (type) => {
    setFilterType(type || null);
  };

  if (!wsId) {
    return (
      <div style={{ padding: 24 }}>
        <Card><Title level={5} type="secondary">请先从知识库页面选择工作空间</Title></Card>
      </div>
    );
  }

  const nodeData = selectedNode?.data?.data || {};

  return (
    <div ref={(el) => { if (el && fullscreen) el.requestFullscreen?.().catch(() => {}); }} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Toolbar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: '#fff', borderBottom: '1px solid #e8e8e8', flexWrap: 'wrap', gap: 8 }}>
        <Space>
          {workspace && <Tag color="purple">{workspace.name}</Tag>}
          <Select size="small" value={layout} onChange={changeLayout} style={{ width: 100 }} options={LAYOUT_OPTIONS} />
          <Select size="small" placeholder="筛选类型" allowClear style={{ width: 120 }}
            value={filterType} onChange={handleFilterChange}
            options={Object.keys(entityColors).map((k) => ({ value: k, label: k }))} />
        </Space>
        <Space>
          <Input size="small" prefix={<SearchOutlined />} placeholder="搜索实体..." value={searchText}
            onChange={(e) => setSearchText(e.target.value)} style={{ width: 160 }} onPressEnter={handleSearch} />
          <Tooltip title="适应画布"><Button size="small" icon={<AimOutlined />} onClick={() => graphRef.current?.fitView()} /></Tooltip>
          <Tooltip title="放大"><Button size="small" icon={<ZoomInOutlined />} onClick={() => handleZoom(0.2)} /></Tooltip>
          <Tooltip title="缩小"><Button size="small" icon={<ZoomOutOutlined />} onClick={() => handleZoom(-0.2)} /></Tooltip>
          <Tooltip title="刷新"><Button size="small" icon={<ReloadOutlined />} onClick={loadData} loading={loading} /></Tooltip>
          <Tooltip title="导出"><Button size="small" icon={<DownloadOutlined />} onClick={() => graphRef.current?.toDataURL().then((url) => { const a = document.createElement('a'); a.href = url; a.download = 'graphrag.png'; a.click(); }).catch(() => {})} /></Tooltip>
          <Tooltip title="全屏"><Button size="small" icon={fullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />} onClick={() => setFullscreen(!fullscreen)} /></Tooltip>
        </Space>
      </div>

      {/* Graph Canvas + Sidebar */}
      <div style={{ flex: 1, display: 'flex', position: 'relative' }}>
        <div ref={containerRef} style={{ flex: 1, minHeight: 500 }} />

        {selectedNode && (
          <div style={{ background: '#fff', borderLeft: '1px solid #e8e8e8', padding: 16, overflow: 'auto', flexShrink: 0, width: 300 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <Title level={5} style={{ margin: 0 }}>实体详情</Title>
              <Button size="small" type="text" icon={<CloseOutlined />} onClick={() => setSelectedNode(null)} />
            </div>
            <div style={{ marginBottom: 8 }}>
              <Text strong>ID: </Text><Text code style={{ fontSize: 11 }}>{selectedNode.id}</Text>
            </div>
            <div style={{ marginBottom: 8 }}>
              <Text strong>名称: </Text><Text>{nodeData.label || nodeData.label || '-'}</Text>
            </div>
            <div style={{ marginBottom: 8 }}>
              <Text strong>类型: </Text>
              <Tag color={entityColors[nodeData.entity_type] ? undefined : 'default'}
                style={entityColors[nodeData.entity_type] ? { background: entityColors[nodeData.entity_type], color: '#fff', borderColor: entityColors[nodeData.entity_type] } : {}}>
                {nodeData.entity_type || 'Unknown'}
              </Tag>
            </div>
            {nodeData.description && (
              <div style={{ marginBottom: 12 }}>
                <Text strong>描述</Text>
                <div style={{ background: '#f8f9fc', borderRadius: 6, padding: 8, marginTop: 4, fontSize: 13, lineHeight: '20px' }}>
                  {nodeData.description}
                </div>
              </div>
            )}
            <div style={{ marginBottom: 12 }}>
              <Text strong>展开深度: </Text>
              <Slider min={1} max={3} value={depth} onChange={setDepth} />
            </div>
            <Button type="primary" icon={<ExpandOutlined />} block onClick={expandNeighbors}>展开邻居</Button>
          </div>
        )}
      </div>

      {/* Status Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 16px', background: '#fafbfc', borderTop: '1px solid #e8e8e8' }}>
        <Space size="large">
          <Text type="secondary">实体: <Text strong>{stats.entity_count}</Text></Text>
          <Text type="secondary">关系: <Text strong>{stats.relation_count}</Text></Text>
          <Text type="secondary">布局: <Tag>{LAYOUT_OPTIONS.find((o) => o.value === layout)?.label}</Tag></Text>
        </Space>
        <Space>
          {Object.entries(entityColors).map(([type, color]) => (
            <Space key={type} size={4}><Badge color={color} /><Text style={{ fontSize: 12 }}>{type}</Text></Space>
          ))}
        </Space>
      </div>
    </div>
  );
}
