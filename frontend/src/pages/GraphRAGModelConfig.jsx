import { useEffect, useState, useCallback } from 'react';
import {
  Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Tag, Typography,
  message, Empty, Tabs, Badge, Tooltip,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, EditOutlined, StarOutlined, StarFilled,
  ApiOutlined, RobotOutlined, ThunderboltOutlined, EyeOutlined,
} from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';
import * as graphragApi from '../api/graphrag';

const { Title, Text, Paragraph } = Typography;

const MODEL_TYPES = [
  { key: 'llm', label: 'LLM', icon: <RobotOutlined />, desc: '大语言模型 — 实体抽取、关系抽取、问答生成' },
  { key: 'embedding', label: 'Embedding', icon: <ThunderboltOutlined />, desc: '向量嵌入模型 — 文本向量化' },
  { key: 'rerank', label: 'Rerank', icon: <EyeOutlined />, desc: '重排序模型 — 检索结果重排' },
  { key: 'vlm', label: 'VLM', icon: <ApiOutlined />, desc: '视觉语言模型 — 图文理解' },
];

const DEFAULT_PROVIDERS = {
  llm: [
    { provider: 'deepseek', models: ['deepseek-chat', 'deepseek-reasoner'] },
    { provider: 'openai', models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'] },
    { provider: 'anthropic', models: ['claude-opus-4-20250514', 'claude-sonnet-4-20250514'] },
  ],
  embedding: [
    { provider: 'deepseek', models: ['deepseek-embedding'] },
    { provider: 'openai', models: ['text-embedding-3-small', 'text-embedding-3-large'] },
  ],
  rerank: [
    { provider: 'cohere', models: ['rerank-english-v3.0', 'rerank-multilingual-v3.0'] },
    { provider: 'jina', models: ['jina-reranker-v2'] },
  ],
  vlm: [
    { provider: 'openai', models: ['gpt-4o', 'gpt-4-vision-preview'] },
    { provider: 'anthropic', models: ['claude-sonnet-4-20250514'] },
  ],
};

export default function GraphRAGModelConfig() {
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState(null);
  const [activeType, setActiveType] = useState('llm');
  const [form] = Form.useForm();

  const loadConfigs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await graphragApi.listModelConfigs('', activeType);
      if (res.code === 0) setConfigs(res.data || []);
    } catch { message.error('加载配置失败'); }
    finally { setLoading(false); }
  }, [activeType]);

  useEffect(() => { loadConfigs(); }, [loadConfigs]);

  const handleCreateOrUpdate = async () => {
    try {
      const values = await form.validateFields();
      let res;
      if (editingConfig) {
        res = await graphragApi.updateModelConfig(editingConfig.config_id, values);
      } else {
        res = await graphragApi.createModelConfig({ model_type: activeType, ...values });
      }
      if (res.code === 0) {
        message.success(editingConfig ? '已更新' : '已创建');
        setModalOpen(false);
        setEditingConfig(null);
        form.resetFields();
        loadConfigs();
      }
    } catch { /* validation */ }
  };

  const handleEdit = (config) => {
    setEditingConfig(config);
    form.setFieldsValue({
      workspace_id: config.workspace_id || '',
      provider_name: config.provider_name,
      model_name: config.model_name,
      config: JSON.stringify(config.config || {}, null, 2),
      is_default: config.is_default || false,
    });
    setModalOpen(true);
  };

  const handleDelete = async (id) => {
    try {
      const res = await graphragApi.deleteModelConfig(id);
      if (res.code === 0) {
        message.success('已删除');
        loadConfigs();
      }
    } catch { message.error('删除失败'); }
  };

  const openCreate = () => {
    setEditingConfig(null);
    form.resetFields();
    form.setFieldsValue({ is_default: false, config: '{}' });
    setModalOpen(true);
  };

  const [selectedProvider, setSelectedProvider] = useState('');
  const providers = DEFAULT_PROVIDERS[activeType] || [];

  const tabItems = MODEL_TYPES.map((mt) => ({
    key: mt.key,
    label: <Space size={4}>{mt.icon}{mt.label}</Space>,
    children: (
      <div style={{ padding: '16px 0' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Text type="secondary">{mt.desc}</Text>
          <Button type="primary" size="small" icon={<PlusOutlined />} onClick={openCreate}>添加配置</Button>
        </div>

        {configs.length === 0 && !loading ? (
          <Empty description={`暂无 ${mt.label} 配置`} />
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
            {configs.map((cfg) => (
              <Card
                key={cfg.config_id}
                size="small"
                title={
                  <Space>
                    {mt.icon}
                    <Text strong>{cfg.model_name}</Text>
                    <Tag color="blue">@{cfg.provider_name}</Tag>
                    {cfg.is_default && <Tag color="purple">默认</Tag>}
                  </Space>
                }
                extra={
                  <Space>
                    <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(cfg)} />
                    <Popconfirm title="确定删除?" onConfirm={() => handleDelete(cfg.config_id)}>
                      <Button size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </Space>
                }
              >
                <div style={{ fontSize: 12 }}>
                  {cfg.workspace_id && <Text type="secondary">空间: {cfg.workspace_id}</Text>}
                  {cfg.config && Object.keys(cfg.config).length > 0 && (
                    <div style={{ marginTop: 4 }}>
                      <Text type="secondary">配置参数:</Text>
                      <pre style={{ background: '#f8f9fc', padding: 6, borderRadius: 4, fontSize: 11, marginTop: 4, maxHeight: 80, overflow: 'auto' }}>
                        {JSON.stringify(cfg.config, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    ),
  }));

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ marginBottom: 16 }}>模型配置</Title>
      <Tabs activeKey={activeType} onChange={setActiveType} items={tabItems} />

      <Modal
        title={editingConfig ? '编辑模型配置' : '添加模型配置'}
        open={modalOpen}
        onOk={handleCreateOrUpdate}
        onCancel={() => { setModalOpen(false); setEditingConfig(null); form.resetFields(); }}
        width={520}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="workspace_id" label="工作空间 (空=全局)">
            <Input placeholder="留空表示全局配置" />
          </Form.Item>
          <Form.Item name="provider_name" label="模型提供商" rules={[{ required: true }]}>
            <Select
              placeholder="选择提供商"
              onChange={(v) => setSelectedProvider(v)}
              options={providers.map((p) => ({ value: p.provider, label: p.provider }))}
            />
          </Form.Item>
          <Form.Item name="model_name" label="模型名称" rules={[{ required: true }]}>
            <Select placeholder="选择模型"
              options={(providers.find((p) => p.provider === (form.getFieldValue('provider_name') || selectedProvider))?.models || []).map((m) => ({ value: m, label: m }))} />
          </Form.Item>
          <Form.Item name="config" label="配置参数 (JSON)">
            <Input.TextArea rows={4} placeholder='{"temperature": 0.1, "max_tokens": 4096}' />
          </Form.Item>
          <Form.Item name="is_default" valuePropName="checked" label="设为默认">
            <Select options={[{ value: true, label: '是' }, { value: false, label: '否' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
