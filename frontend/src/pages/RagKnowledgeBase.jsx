import { useState, useEffect, useCallback } from 'react';
import {
  Card, Table, Button, Space, Typography, message, Popconfirm, Tag, Tooltip, Modal, Input,
} from 'antd';
import { PlusOutlined, DeleteOutlined, ReloadOutlined, SearchOutlined, UploadOutlined } from '@ant-design/icons';
import { listKnowledgeBases, createKnowledgeBase, deleteKnowledgeBase } from '../api/rag';

const { Title, Text } = Typography;

export default function KnowledgeBasePage() {
  const [kbs, setKbs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [creating, setCreating] = useState(false);

  const fetchKBs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listKnowledgeBases();
      if (res.code === 0) setKbs(res.data?.items || res.data || []);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchKBs(); }, [fetchKBs]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const res = await createKnowledgeBase(newName.trim(), newDesc.trim());
      if (res.code === 0) {
        message.success('知识库已创建');
        setModalOpen(false);
        setNewName('');
        setNewDesc('');
        fetchKBs();
      }
    } finally { setCreating(false); }
  };

  const handleDelete = async (kbId) => {
    const res = await deleteKnowledgeBase(kbId);
    if (res.code === 0) { message.success('已删除'); fetchKBs(); }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name', render: (t) => <Text strong>{t}</Text> },
    { title: 'ID', dataIndex: 'kb_id', key: 'id', width: 200, render: (v) => <Text code style={{fontSize:12}}>{v}</Text> },
    { title: '描述', dataIndex: 'description', key: 'desc', ellipsis: true },
    { title: '创建时间', dataIndex: 'created_at', key: 'created', width: 180, render: (v) => v ? new Date(v).toLocaleString() : '-' },
    {
      title: '操作', key: 'actions', width: 200,
      render: (_, r) => (
        <Space>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.kb_id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>知识库管理</Title>
          <Text type="secondary">管理 RAG 知识库</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchKBs}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建知识库</Button>
        </Space>
      </div>

      <Card>
        <Table columns={columns} dataSource={kbs} rowKey="kb_id" loading={loading} pagination={false} />
      </Card>

      <Modal
        title="新建知识库"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
        confirmLoading={creating}
        okText="创建" cancelText="取消"
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text strong>名称</Text>
            <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="知识库名称" onPressEnter={handleCreate} />
          </div>
          <div>
            <Text strong>描述</Text>
            <Input.TextArea value={newDesc} onChange={(e) => setNewDesc(e.target.value)} placeholder="可选描述" rows={3} />
          </div>
        </Space>
      </Modal>
    </div>
  );
}
