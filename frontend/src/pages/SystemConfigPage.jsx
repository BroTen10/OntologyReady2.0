import { useState, useEffect, useCallback } from 'react';
import { Card, Form, Input, Select, Switch, Button, Space, Typography, message, Divider, InputNumber, Alert, Spin } from 'antd';
import { SaveOutlined, ReloadOutlined, SettingOutlined } from '@ant-design/icons';
import api from '../api/client';

const { Title, Text } = Typography;

export default function SystemConfigPage() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const fetchConfig = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/system-config');
      if (res.data.code === 0) {
        const data = res.data.data || {};
        setConfig(data);
        form.setFieldsValue(data);
      }
    } catch { /* */ }
    setLoading(false);
  }, [form]);

  useEffect(() => { fetchConfig(); }, [fetchConfig]);

  const handleSave = async () => {
    const values = form.getFieldsValue();
    setSaving(true);
    try {
      const res = await api.post('/admin/system-config', values);
      if (res.data.code === 0) {
        message.success('系统配置已保存');
        setConfig(res.data.data);
      }
    } catch { message.error('保存失败'); }
    setSaving(false);
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>;

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}><SettingOutlined style={{ marginRight: 8 }} />系统配置</Title>
          <Text type="secondary">全局系统参数、Provider 配置与连接测试</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchConfig}>刷新</Button>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>保存配置</Button>
        </Space>
      </div>

      <Form form={form} layout="vertical">
        <Card title="数据库连接" style={{ marginBottom: 16 }}>
          <Form.Item name="db_host" label="主机">
            <Input placeholder="localhost" />
          </Form.Item>
          <Form.Item name="db_port" label="端口">
            <InputNumber min={1} max={65535} style={{ width: '100%' }} placeholder="5432" />
          </Form.Item>
          <Form.Item name="db_name" label="数据库名">
            <Input placeholder="ontology" />
          </Form.Item>
          <Form.Item name="db_user" label="用户名">
            <Input placeholder="postgres" />
          </Form.Item>
          <Form.Item name="db_password" label="密码">
            <Input.Password placeholder="支持 ${env:DB_PASSWORD}" />
          </Form.Item>
        </Card>

        <Card title="文档引擎" style={{ marginBottom: 16 }}>
          <Form.Item name="document_engine_type" label="引擎类型">
            <Select options={[
              { value: 'postgres', label: 'PostgreSQL (默认)' },
              { value: 'opensearch', label: 'OpenSearch' },
            ]} />
          </Form.Item>
        </Card>

        <Card title="对象存储 (OSS)" style={{ marginBottom: 16 }}>
          <Form.Item name="storage_type" label="存储类型">
            <Select options={[
              { value: 'local', label: '本地存储' },
              { value: 'minio', label: 'MinIO' },
              { value: 's3', label: 'AWS S3' },
            ]} />
          </Form.Item>
          <Form.Item name="storage_endpoint" label="存储端点">
            <Input placeholder="http://localhost:9000" />
          </Form.Item>
          <Form.Item name="storage_access_key" label="Access Key">
            <Input placeholder="支持 ${env:MINIO_ACCESS_KEY}" />
          </Form.Item>
          <Form.Item name="storage_secret_key" label="Secret Key">
            <Input.Password placeholder="支持 ${env:MINIO_SECRET_KEY}" />
          </Form.Item>
          <Form.Item name="storage_bucket" label="Bucket">
            <Input placeholder="ontology-files" />
          </Form.Item>
        </Card>

        <Card title="LLM / Embedding Provider" style={{ marginBottom: 16 }}>
          <Form.Item name="llm_provider" label="LLM Provider">
            <Select options={[{ value: 'deepseek', label: 'DeepSeek' }, { value: 'openai', label: 'OpenAI' }, { value: 'ollama', label: 'Ollama' }]} />
          </Form.Item>
          <Form.Item name="llm_model" label="LLM 模型">
            <Input placeholder="deepseek-chat" />
          </Form.Item>
          <Form.Item name="llm_api_key" label="LLM API Key">
            <Input.Password placeholder="支持 ${env:DEEPSEEK_API_KEY}" />
          </Form.Item>
          <Form.Item name="embedding_provider" label="Embedding Provider">
            <Select options={[{ value: 'deepseek', label: 'DeepSeek' }, { value: 'openai', label: 'OpenAI' }, { value: 'ollama', label: 'Ollama' }]} />
          </Form.Item>
          <Form.Item name="embedding_model" label="Embedding 模型">
            <Input placeholder="deepseek-embedding" />
          </Form.Item>
        </Card>

        <Card title="系统参数" style={{ marginBottom: 16 }}>
          <Form.Item name="default_page_size" label="默认分页大小">
            <InputNumber min={5} max={100} style={{ width: '100%' }} placeholder="20" />
          </Form.Item>
          <Form.Item name="session_timeout_minutes" label="会话超时 (分钟)">
            <InputNumber min={5} max={1440} style={{ width: '100%' }} placeholder="30" />
          </Form.Item>
          <Form.Item name="access_token_expire_minutes" label="Access Token 有效期 (分钟)">
            <InputNumber min={1} max={1440} style={{ width: '100%' }} placeholder="15" />
          </Form.Item>
          <Form.Item name="refresh_token_expire_days" label="Refresh Token 有效期 (天)">
            <InputNumber min={1} max={90} style={{ width: '100%' }} placeholder="7" />
          </Form.Item>
        </Card>

        <Alert
          type="info"
          message="配置优先级: 环境变量 > .env 文件 > 数据库 system_config > 代码默认值"
          description="修改后即时生效，无需重启服务。使用 ${env:VAR_NAME} 语法引用环境变量。"
          showIcon
        />
      </Form>
    </div>
  );
}
