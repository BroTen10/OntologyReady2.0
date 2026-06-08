import { useState, useEffect, useCallback } from 'react';
import {
  Card, Table, Button, Space, Typography, message, Popconfirm, Modal, Input,
  Tabs, Tag, Statistic, Row, Col, Select, Descriptions, Progress,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, ReloadOutlined, ExperimentOutlined,
  UploadOutlined, PlayCircleOutlined, SwapOutlined,
} from '@ant-design/icons';
import * as evalApi from '../api/evaluation';

const { Title, Text } = Typography;

export default function RagEvalPage() {
  const [activeTab, setActiveTab] = useState('datasets');
  const [datasets, setDatasets] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);

  const [dsModalOpen, setDsModalOpen] = useState(false);
  const [dsName, setDsName] = useState('');
  const [dsDesc, setDsDesc] = useState('');
  const [dsSaving, setDsSaving] = useState(false);

  const [runModalOpen, setRunModalOpen] = useState(false);
  const [runDsId, setRunDsId] = useState(null);
  const [runSaving, setRunSaving] = useState(false);

  const [compareModalOpen, setCompareModalOpen] = useState(false);
  const [compareIds, setCompareIds] = useState([]);
  const [compareResult, setCompareResult] = useState(null);
  const [comparing, setComparing] = useState(false);

  const fetchDatasets = useCallback(async () => {
    setLoading(true);
    try {
      const res = await evalApi.listEvaluationDatasets();
      if (res.code === 0) setDatasets(res.data?.items || res.data || []);
    } finally { setLoading(false); }
  }, []);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    try {
      const res = await evalApi.listRuns();
      if (res.code === 0) setRuns(res.data?.items || res.data || []);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (activeTab === 'datasets') fetchDatasets();
    else fetchRuns();
  }, [activeTab, fetchDatasets, fetchRuns]);

  const handleCreateDs = async () => {
    if (!dsName.trim()) return;
    setDsSaving(true);
    try {
      const res = await evalApi.createEvaluationDataset({ name: dsName.trim(), description: dsDesc.trim() });
      if (res.code === 0) {
        message.success('评测数据集已创建');
        setDsModalOpen(false);
        setDsName('');
        setDsDesc('');
        fetchDatasets();
      }
    } finally { setDsSaving(false); }
  };

  const handleDeleteDs = async (id) => {
    const res = await evalApi.deleteEvaluationDataset(id);
    if (res.code === 0) { message.success('已删除'); fetchDatasets(); }
  };

  const handleCreateRun = async () => {
    if (!runDsId) return;
    setRunSaving(true);
    try {
      const res = await evalApi.createRun({ dataset_id: runDsId, kb_id: runDsId });
      if (res.code === 0) {
        message.success('评测运行已启动');
        setRunModalOpen(false);
        setRunDsId(null);
        fetchRuns();
        setActiveTab('runs');
      }
    } finally { setRunSaving(false); }
  };

  const handleCompare = async () => {
    if (compareIds.length < 2) return;
    setComparing(true);
    try {
      const res = await evalApi.compareRuns({ run_ids: compareIds });
      if (res.code === 0) setCompareResult(res.data);
    } finally { setComparing(false); }
  };

  const datasetColumns = [
    { title: '名称', dataIndex: 'name', render: (v) => <Text strong>{v}</Text> },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    { title: '问题数', dataIndex: 'question_count', width: 90, render: (v) => v ?? '-' },
    {
      title: '操作', key: 'actions', width: 160,
      render: (_, r) => (
        <Space>
          <Button size="small" onClick={() => { setRunDsId(r.id); setRunModalOpen(true); }}>运行评测</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDeleteDs(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const runColumns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '数据集', dataIndex: 'dataset_name', render: (v) => v || '-' },
    { title: '状态', dataIndex: 'status', width: 100, render: (v) => {
      const colors = { running: 'blue', completed: 'green', failed: 'red', pending: 'default' };
      return <Tag color={colors[v] || 'default'}>{v}</Tag>;
    }},
    { title: '准确率', dataIndex: 'accuracy', width: 90, render: (v) => v !== undefined ? `${(v*100).toFixed(1)}%` : '-' },
    { title: '召回率', dataIndex: 'recall', width: 90, render: (v) => v !== undefined ? `${(v*100).toFixed(1)}%` : '-' },
    { title: '响应时间', dataIndex: 'avg_response_time_ms', width: 110, render: (v) => v ? `${v.toFixed(0)}ms` : '-' },
    { title: '创建时间', dataIndex: 'created_at', width: 170, render: (v) => v ? new Date(v).toLocaleString() : '-' },
    {
      title: '操作', key: 'actions', width: 80,
      render: (_, r) => (
        <Popconfirm title="确定删除？" onConfirm={async () => { await evalApi.deleteRun(r.id); fetchRuns(); }}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  const tabs = [
    {
      key: 'datasets', label: `评测数据集 (${datasets.length})`, children: (
        <div>
          <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: 16 }} onClick={() => setDsModalOpen(true)}>新建数据集</Button>
          <Table columns={datasetColumns} dataSource={datasets} rowKey="id" loading={loading} size="small" />
        </div>
      ),
    },
    {
      key: 'runs', label: `评测运行 (${runs.length})`, children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => setRunModalOpen(true)}>新建运行</Button>
            <Button icon={<SwapOutlined />} onClick={() => setCompareModalOpen(true)} disabled={runs.length < 2}>对比运行</Button>
          </Space>
          <Table columns={runColumns} dataSource={runs} rowKey="id" loading={loading} size="small" />
        </div>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={4}><ExperimentOutlined style={{ marginRight: 8 }} />RAG 评测</Title>
        <Text type="secondary">创建评测数据集、发起评测运行、对比不同运行结果</Text>
      </div>

      <Card><Tabs activeKey={activeTab} onChange={setActiveTab} items={tabs} /></Card>

      <Modal title="新建评测数据集" open={dsModalOpen} onOk={handleCreateDs} onCancel={() => setDsModalOpen(false)} confirmLoading={dsSaving}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div><Text strong>名称</Text><Input value={dsName} onChange={(e) => setDsName(e.target.value)} onPressEnter={handleCreateDs} /></div>
          <div><Text strong>描述</Text><Input.TextArea value={dsDesc} onChange={(e) => setDsDesc(e.target.value)} rows={3} /></div>
        </Space>
      </Modal>

      <Modal title="新建评测运行" open={runModalOpen} onOk={handleCreateRun} onCancel={() => setRunModalOpen(false)} confirmLoading={runSaving}>
        <div><Text strong>评测数据集</Text>
          <Select value={runDsId} onChange={setRunDsId} style={{ width: '100%' }} placeholder="选择数据集"
            options={datasets.map(d => ({ value: d.id, label: d.name }))} />
        </div>
      </Modal>

      <Modal title="对比运行结果" open={compareModalOpen} onOk={handleCompare} onCancel={() => setCompareModalOpen(false)} confirmLoading={comparing} width={700}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Select mode="multiple" value={compareIds} onChange={setCompareIds} style={{ width: '100%' }} placeholder="选择 2+ 运行"
            options={runs.map(r => ({ value: r.id, label: `Run #${r.id} (${r.dataset_name || '-'})` }))} />
          {compareResult && (
            <Card size="small">
              <Row gutter={16}>
                {compareResult.runs?.map((r, i) => (
                  <Col span={12} key={i}>
                    <Descriptions size="small" title={`Run #${r.id}`} column={1}>
                      <Descriptions.Item label="准确率">{(r.accuracy*100).toFixed(1)}%</Descriptions.Item>
                      <Descriptions.Item label="召回率">{(r.recall*100).toFixed(1)}%</Descriptions.Item>
                    </Descriptions>
                  </Col>
                ))}
              </Row>
            </Card>
          )}
        </Space>
      </Modal>
    </div>
  );
}
