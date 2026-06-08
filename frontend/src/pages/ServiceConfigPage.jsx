import { useState, useEffect, useCallback } from 'react';
import { Card, Form, Input, Select, Button, Switch, Space, Typography, message, Divider, InputNumber, Alert } from 'antd';
import { SaveOutlined, ReloadOutlined, ApiOutlined, DatabaseOutlined, CloudOutlined } from '@ant-design/icons';
import api from '../api/client';

const { Title, Text } = Typography;

export default function ServiceConfigPage() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const fetchConfig = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/system-config');
      if (res.data.code === 0) {
        setConfig(res.data.data);
        form.setFieldsValue(res.data.data);
      }
    } catch { /* use defaults */ }
    setLoading(false);
  }, [form]);

  useEffect(() => { fetchConfig(); }, [fetchConfig]);

  const handleSave = async () => {
    const values = form.getFieldsValue();
    setSaving(true);
    try {
      const res = await api.post('/admin/system-config', values);
      if (res.data.code === 0) {
        message.success('服务配置已保存');
        setConfig(res.data.data);
      }
    } catch { message.error('保存失败'); }
    setSaving(false);
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}><ApiOutlined style={{ marginRight: 8 }} />服务配置</Title>
          <Text type="secondary">配置 RAG 引擎底层服务参数</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchConfig}>刷新</Button>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>保存配置</Button>
        </Space>
      </div>

      <Form form={form} layout="vertical">
        <Card title={<><DatabaseOutlined /> 文档引擎</>} style={{ marginBottom: 16 }}>
          <Form.Item name="document_engine_type" label="文档引擎类型">
            <Select options={[{value:'postgres',label:'PostgreSQL'},{value:'opensearch',label:'OpenSearch'}]} />
          </Form.Item>
          <Form.Item name="embedding_model" label="Embedding 模型">
            <Input placeholder="如 deepseek-embedding" />
          </Form.Item>
          <Form.Item name="chunk_size" label="分块大小">
            <InputNumber min={100} max={5000} step={100} style={{width:'100%'}} placeholder="1200" />
          </Form.Item>
          <Form.Item name="chunk_overlap" label="分块重叠">
            <InputNumber min={0} max={500} step={10} style={{width:'100%'}} placeholder="100" />
          </Form.Item>
        </Card>

        <Card title={<><CloudOutlined /> 对象存储</>} style={{ marginBottom: 16 }}>
          <Form.Item name="storage_type" label="存储类型">
            <Select options={[{value:'local',label:'本地存储'},{value:'minio',label:'MinIO'},{value:'s3',label:'AWS S3'}]} />
          </Form.Item>
          <Form.Item name="storage_endpoint" label="存储端点">
            <Input placeholder="http://localhost:9000" />
          </Form.Item>
          <Form.Item name="storage_bucket" label="Bucket">
            <Input placeholder="ontology-files" />
          </Form.Item>
        </Card>

        <Card title="系统参数" style={{ marginBottom: 16 }}>
          <Form.Item name="default_page_size" label="默认分页大小">
            <InputNumber min={5} max={100} style={{width:'100%'}} placeholder="20" />
          </Form.Item>
          <Form.Item name="session_timeout_minutes" label="会话超时 (分钟)">
            <InputNumber min={5} max={1440} style={{width:'100%'}} placeholder="30" />
          </Form.Item>
        </Card>

        <Alert
          type="info"
          message="配置提示"
          description="修改后即时生效，不需要重启服务。支持使用 ${env:VAR_NAME} 语法引用环境变量。配置优先级: 环境变量 > 系统配置 > 代码默认值。"
          showIcon
        />
      </Form>
    </div>
  );
}
