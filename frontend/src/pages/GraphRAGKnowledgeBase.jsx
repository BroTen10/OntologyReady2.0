import { useEffect, useState, useCallback } from 'react';
import { Button, Card, Form, Input, Modal, Popconfirm, Space, Tag, Typography, message, Empty } from 'antd';
import { PlusOutlined, DeleteOutlined, StarOutlined, StarFilled, SettingOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import * as graphragApi from '../api/graphrag';

const { Title, Text, Paragraph } = Typography;

export default function GraphRAGKnowledgeBase() {
  const [workspaces, setWorkspaces] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const loadWorkspaces = useCallback(async () => {
    setLoading(true);
    try {
      const res = await graphragApi.listWorkspaces();
      if (res.code === 0) setWorkspaces(res.data || []);
    } catch { message.error('加载工作空间失败'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadWorkspaces(); }, [loadWorkspaces]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      const res = await graphragApi.createWorkspace(values);
      if (res.code === 0) {
        message.success('工作空间创建成功');
        setModalOpen(false);
        form.resetFields();
        loadWorkspaces();
      }
    } catch { /* validation error */ }
  };

  const handleDelete = async (id) => {
    try {
      const res = await graphragApi.deleteWorkspace(id);
      if (res.code === 0) {
        message.success('已删除');
        loadWorkspaces();
      }
    } catch { message.error('删除失败'); }
  };

  const handleSetDefault = async (id) => {
    try {
      const res = await graphragApi.setDefaultWorkspace(id);
      if (res.code === 0) {
        message.success('已设为默认空间');
        loadWorkspaces();
      }
    } catch { message.error('操作失败'); }
  };

  const cols = [
    { title: '名称', dataIndex: 'name', key: 'name', render: (text, rec) => <Text strong>{text}{rec.is_default ? <Tag color="purple" style={{ marginLeft: 8 }}>默认</Tag> : null}</Text> },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (v) => v ? new Date(v).toLocaleString() : '-' },
    {
      title: '操作', key: 'actions', render: (_, rec) => (
        <Space>
          <Button size="small" onClick={() => navigate(`/graphrag/documents?ws=${rec.workspace_id}`)}>文档</Button>
          <Button size="small" onClick={() => navigate(`/graphrag/graph?ws=${rec.workspace_id}`)}>图谱</Button>
          <Button size="small" onClick={() => navigate(`/graphrag/qa?ws=${rec.workspace_id}`)}>问答</Button>
          <Button size="small" icon={rec.is_default ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
            onClick={() => handleSetDefault(rec.workspace_id)} title="设为默认" />
          <Popconfirm title="确定删除此空间?" onConfirm={() => handleDelete(rec.workspace_id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>GraphRAG 知识库</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建工作空间</Button>
      </div>

      {workspaces.length === 0 && !loading ? (
        <Card><Empty description="暂无工作空间，点击上方新建" /></Card>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
          {workspaces.map((ws) => (
            <Card
              key={ws.workspace_id}
              hoverable
              title={
                <Space>
                  {ws.name}
                  {ws.is_default && <Tag color="purple">默认</Tag>}
                </Space>
              }
              extra={
                <Popconfirm title="确定删除?" onConfirm={() => handleDelete(ws.workspace_id)}>
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              }
              actions={[
                <Button type="link" onClick={() => navigate(`/graphrag/documents?ws=${ws.workspace_id}`)}>文档</Button>,
                <Button type="link" onClick={() => navigate(`/graphrag/graph?ws=${ws.workspace_id}`)}>图谱</Button>,
                <Button type="link" onClick={() => navigate(`/graphrag/qa?ws=${ws.workspace_id}`)}>问答</Button>,
              ]}
            >
              <Paragraph type="secondary" ellipsis={{ rows: 2 }}>{ws.description || '暂无描述'}</Paragraph>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {ws.created_at ? new Date(ws.created_at).toLocaleString() : ''}
              </Text>
              {!ws.is_default && (
                <div style={{ marginTop: 8 }}>
                  <Button size="small" icon={<StarOutlined />} onClick={() => handleSetDefault(ws.workspace_id)}>设为默认</Button>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      <Modal title="新建工作空间" open={modalOpen} onOk={handleCreate} onCancel={() => { setModalOpen(false); form.resetFields(); }}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="空间名称" rules={[{ required: true, message: '请输入空间名称' }]}>
            <Input placeholder="如: 企业知识库" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="描述此工作空间的用途" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
