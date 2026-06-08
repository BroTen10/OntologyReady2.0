import { useState, useEffect, useCallback } from 'react';
import { Card, Button, Table, Space, Typography, Tag, message, Form, Select, Input, Modal, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined, ReloadOutlined, SettingOutlined } from '@ant-design/icons';
import * as graphragApi from '../api/graphrag';

const { Title, Text } = Typography;

const MODEL_TYPES = [
  { value: 'llm', label: 'LLM' },
  { value: 'embedding', label: 'Embedding' },
  { value: 'rerank', label: 'Rerank' },
  { value: 'vlm', label: 'VLM' },
];

const PROVIDERS = [
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'ollama', label: 'Ollama' },
];

export default function RagModelConfigPage() {
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  const fetchConfigs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await graphragApi.listModelConfigs();
      if (res.code === 0) setConfigs(res.data?.items || res.data || []);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchConfigs(); }, [fetchConfigs]);

  const openModal = (record) => {
    if (record) {
      setEditing(record);
      form.setFieldsValue(record);
    } else {
      setEditing(null);
      form.resetFields();
    }
    setModalOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      let res;
      if (editing) {
        res = await graphragApi.updateModelConfig(editing.id, values);
      } else {
        res = await graphragApi.createModelConfig(values);
      }
      if (res.code === 0) {
        message.success(editing ? '已更新' : '已创建');
        setModalOpen(false);
        fetchConfigs();
      }
    } finally { setSaving(false); }
  };

  const handleDelete = async (id) => {
    const res = await graphragApi.deleteModelConfig(id);
    if (res.code === 0) { message.success('已删除'); fetchConfigs(); }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', render: (v) => <Text strong>{v}</Text> },
    { title: '类型', dataIndex: 'model_type', width: 100, render: (v) => <Tag color="purple">{v}</Tag> },
    { title: '模型', dataIndex: 'model_name', render: (v) => <Text code>{v}</Text> },
    { title: '提供商', dataIndex: 'provider', width: 110, render: (v) => <Tag>{v}</Tag> },
    { title: '默认', dataIndex: 'is_default', width: 70, render: (v) => v ? <Tag color="green">是</Tag> : <Tag>否</Tag> },
    {
      title: '操作', key: 'actions', width: 120,
      render: (_, r) => (
        <Space>
          <Button size="small" onClick={() => openModal(r)}>编辑</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.id)}>
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
          <Title level={4} style={{ margin: 0 }}><SettingOutlined style={{ marginRight: 8 }} />模型配置</Title>
          <Text type="secondary">管理 RAG 引擎使用的 LLM、Embedding、Rerank、VLM 模型</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchConfigs}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => openModal(null)}>新增配置</Button>
        </Space>
      </div>

      <Card>
        <Table columns={columns} dataSource={configs} rowKey="id" loading={loading} size="small" />
      </Card>

      <Modal
        title={editing ? '编辑模型配置' : '新增模型配置'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="配置名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="model_type" label="模型类型" rules={[{ required: true }]}>
            <Select options={MODEL_TYPES} />
          </Form.Item>
          <Form.Item name="model_name" label="模型名称" rules={[{ required: true }]}>
            <Input placeholder="如 deepseek-chat, gpt-4" />
          </Form.Item>
          <Form.Item name="provider" label="提供商" rules={[{ required: true }]}>
            <Select options={PROVIDERS} />
          </Form.Item>
          <Form.Item name="api_key" label="API Key">
            <Input.Password placeholder="如未填则使用系统默认" />
          </Form.Item>
          <Form.Item name="is_default" label="设为默认" valuePropName="checked">
            </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
