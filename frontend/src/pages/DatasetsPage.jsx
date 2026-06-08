import { useState, useEffect, useCallback } from 'react';
import { Table, Button, Space, Modal, Input, Typography, message, Popconfirm, Card, Tooltip } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined, ReloadOutlined, DatabaseOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import * as datasetsApi from '../api/datasets';

const { Title, Text } = Typography;

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const res = await datasetsApi.listDatasets();
      if (res.code === 0) setDatasets(res.data?.items || res.data || []);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      let res;
      if (editing) {
        res = await datasetsApi.updateDataset(editing.dataset_id, { display_name: name.trim(), description: desc.trim() });
      } else {
        res = await datasetsApi.createDataset({ display_name: name.trim(), description: desc.trim() });
      }
      if (res.code === 0) {
        message.success(editing ? '数据集已更新' : '数据集已创建');
        setModalOpen(false);
        setName('');
        setDesc('');
        setEditing(null);
        fetchAll();
      }
    } finally { setSaving(false); }
  };

  const handleEdit = (ds) => {
    setEditing(ds);
    setName(ds.display_name || ds.name || '');
    setDesc(ds.description || '');
    setModalOpen(true);
  };

  const handleDelete = async (id) => {
    const res = await datasetsApi.deleteDataset(id);
    if (res.code === 0) { message.success('已删除'); fetchAll(); }
  };

  const columns = [
    { title: 'ID', dataIndex: 'dataset_id', key: 'id', width: 180, render: (v) => <Text code>{v}</Text> },
    { title: '名称', dataIndex: 'display_name', key: 'name', render: (t, r) => <Text strong>{t || r.name}</Text> },
    { title: '描述', dataIndex: 'description', key: 'desc', ellipsis: true },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created', width: 180,
      render: (v) => v ? new Date(v).toLocaleString() : '-',
    },
    {
      title: '操作', key: 'actions', width: 200,
      render: (_, r) => (
        <Space>
          <Tooltip title="进入数据集"><Button size="small" type="primary" onClick={() => navigate(`/ontology/graph?dataset=${r.dataset_id}`)}>进入</Button></Tooltip>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(r)} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.dataset_id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}><DatabaseOutlined style={{ marginRight: 8 }} />数据集管理</Title>
          <Text type="secondary">每个数据集包含独立的本体定义、实例数据和图谱</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchAll}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); setName(''); setDesc(''); setModalOpen(true); }}>新建数据集</Button>
        </Space>
      </div>

      <Card>
        <Table columns={columns} dataSource={datasets} rowKey="dataset_id" loading={loading} pagination={{ pageSize: 20 }} />
      </Card>

      <Modal
        title={editing ? '编辑数据集' : '新建数据集'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        okText="保存" cancelText="取消"
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text strong>名称</Text>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="数据集名称" onPressEnter={handleSave} />
          </div>
          <div>
            <Text strong>描述</Text>
            <Input.TextArea value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="可选描述" rows={3} />
          </div>
        </Space>
      </Modal>
    </div>
  );
}
