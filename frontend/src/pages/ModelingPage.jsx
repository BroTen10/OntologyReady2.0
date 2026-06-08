import { useState } from 'react';
import { Button, Card, Form, Input, InputNumber, message, Radio, Select, Space, Steps, Switch, Tabs, Tag, Typography, Spin, Collapse, Alert } from 'antd';
import {
  ApiOutlined, DatabaseOutlined, CheckCircleOutlined,
  ThunderboltOutlined, RobotOutlined, EyeOutlined, EditOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { testConnection, analyzeSchema, compileOntology, registerOntology, quickModel } from '../api/modeling';
import { useParams } from 'react-router-dom';

const { Title, Text, Paragraph } = Typography;

export default function ModelingPage() {
  const { dataset_id } = useParams();
  const dataset = dataset_id || '_ontology_default';
  const [step, setStep] = useState(0);
  const [connectionType, setConnectionType] = useState('default');
  const [connecting, setConnecting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [connectionResult, setConnectionResult] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [compileResult, setCompileResult] = useState(null);
  const [registerResult, setRegisterResult] = useState(null);
  const [viewMode, setViewMode] = useState('list');
  const [editingJson, setEditingJson] = useState('');
  const [form] = Form.useForm();

  const handleTestConnection = async () => {
    setConnecting(true);
    try {
      const vals = form.getFieldsValue();
      const params = { connection_type: connectionType };
      if (connectionType === 'parameters') {
        Object.assign(params, { host: vals.host, port: vals.port, database: vals.database, username: vals.username, password: vals.password });
      } else if (connectionType === 'dsn') {
        params.dsn = vals.dsn;
      }
      const { data } = await testConnection(dataset, params);
      setConnectionResult(data.data);
      if (data.code === 0 && data.data.success) {
        message.success(`连接成功: ${data.data.table_count} 张表`);
      } else {
        message.error(data.data?.error || '连接失败');
      }
    } catch { message.error('连接失败'); }
    setConnecting(false);
  };

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      const vals = form.getFieldsValue();
      const params = { connection_type: connectionType, schema_name: vals.schema_name || 'public', business_context: vals.business_context, output_language: vals.output_language || 'zh', exclude_tables: vals.exclude_tables?.split(',').map((s) => s.trim()).filter(Boolean) || [], extract_wide_table_entities: vals.extract_wide || false, timeout_seconds: 300 };
      if (connectionType === 'parameters') {
        Object.assign(params, { host: vals.host, port: vals.port, database: vals.database, username: vals.username, password: vals.password });
      } else if (connectionType === 'dsn') {
        params.dsn = vals.dsn;
      }
      const { data } = await analyzeSchema(dataset, params);
      setAnalysisResult(data.data);
      if (data.code === 0) {
        message.success(`分析完成: ${data.data.tables_analyzed} 张表, ${data.data.object_types?.length || 0} 个类型`);
        setStep(1);
      }
    } catch { message.error('分析失败'); }
    setAnalyzing(false);
  };

  const handleCompile = async () => {
    if (!analysisResult) return;
    try {
      const payload = editingJson ? JSON.parse(editingJson) : { object_types: analysisResult.object_types, link_types: analysisResult.link_types, action_types: analysisResult.action_types };
      const { data } = await compileOntology(dataset, payload);
      setCompileResult(data.data);
      if (data.data.valid) {
        message.success(`编译通过: ${data.data.stats.object_type_count} 个类型`);
        setStep(2);
      } else {
        message.warning(`${data.data.errors.length} 个错误, 已自动修复 ${data.data.auto_fix_count} 处`);
        setStep(2);
      }
    } catch (e) { message.error('编译失败: ' + (e.message || 'JSON 格式错误')); }
  };

  const handleRegister = async () => {
    try {
      const payload = { object_types: compileResult?.compiled?.object_types || [], link_types: compileResult?.compiled?.link_types || [], action_types: compileResult?.compiled?.action_types || [] };
      const { data } = await registerOntology(dataset, payload);
      setRegisterResult(data.data);
      message.success(`注册完成: ${data.data.created} 新建, ${data.data.merged} 合并`);
      setStep(3);
    } catch { message.error('注册失败'); }
  };

  const handleQuickModel = async () => {
    setAnalyzing(true);
    try {
      const vals = form.getFieldsValue();
      const params = { connection_type: connectionType, schema_name: vals.schema_name || 'public', exclude_tables: vals.exclude_tables?.split(',').map((s) => s.trim()).filter(Boolean) || [] };
      if (connectionType === 'parameters') {
        Object.assign(params, { host: vals.host, port: vals.port, database: vals.database, username: vals.username, password: vals.password });
      } else if (connectionType === 'dsn') {
        params.dsn = vals.dsn;
      }
      const { data } = await quickModel(dataset, params);
      if (data.code === 0) {
        setAnalysisResult(data.data);
        message.success(`快速建模: ${data.data.object_types?.length || 0} 个类型`);
        setStep(1);
      }
    } catch { message.error('快速建模失败'); }
    setAnalyzing(false);
  };

  const steps = [
    { title: '连接配置', icon: <ApiOutlined /> },
    { title: '预览结果', icon: <EyeOutlined /> },
    { title: '注册本体', icon: <CheckCircleOutlined /> },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}><RobotOutlined /> LLM 辅助建模</Title>
      <Steps current={step} items={steps} style={{ marginBottom: 24 }} />

      {/* Step 0: Connection */}
      {step === 0 && (
        <Card>
          <Tabs
            items={[
              { key: 'llm', label: <><RobotOutlined /> LLM 建模</> },
              { key: 'quick', label: <><ThunderboltOutlined /> 快速建模</> },
            ]}
          />
          <Form form={form} layout="vertical" style={{ marginTop: 16 }} initialValues={{ schema_name: 'public', output_language: 'zh' }}>
            <Form.Item label="连接方式">
              <Radio.Group value={connectionType} onChange={(e) => setConnectionType(e.target.value)}>
                <Radio.Button value="default">项目默认实例</Radio.Button>
                <Radio.Button value="parameters">连接参数</Radio.Button>
                <Radio.Button value="dsn">DSN 连接串</Radio.Button>
              </Radio.Group>
            </Form.Item>

            {connectionType === 'parameters' && (
              <>
                <Space>
                  <Form.Item name="host" label="主机"><Input placeholder="localhost" /></Form.Item>
                  <Form.Item name="port" label="端口"><InputNumber min={1} max={65535} placeholder="5432" /></Form.Item>
                </Space>
                <Space>
                  <Form.Item name="database" label="数据库"><Input placeholder="mydb" /></Form.Item>
                  <Form.Item name="username" label="用户名"><Input placeholder="postgres" /></Form.Item>
                  <Form.Item name="password" label="密码"><Input.Password placeholder="密码" /></Form.Item>
                </Space>
              </>
            )}

            {connectionType === 'dsn' && (
              <Form.Item name="dsn" label="DSN">
                <Input placeholder="postgresql://user:pass@host:5432/db" />
              </Form.Item>
            )}

            <Space>
              <Form.Item name="schema_name" label="Schema"><Input placeholder="public" /></Form.Item>
              <Form.Item name="exclude_tables" label="排除表"><Input placeholder="逗号分隔" /></Form.Item>
            </Space>

            <Form.Item name="business_context" label="业务背景">
              <Input.TextArea rows={2} placeholder="描述业务场景以帮助 LLM 理解..." />
            </Form.Item>

            <Space>
              <Form.Item name="output_language" label="输出语言">
                <Select style={{ width: 100 }} options={[{ value: 'zh', label: '中文' }, { value: 'en', label: 'English' }]} />
              </Form.Item>
              <Form.Item name="extract_wide" label="提取宽表实体" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Space>

            <Space>
              <Button icon={<ApiOutlined />} loading={connecting} onClick={handleTestConnection}>测试连接</Button>
              <Button type="primary" icon={<RobotOutlined />} loading={analyzing} onClick={handleAnalyze}>LLM 分析</Button>
              <Button icon={<ThunderboltOutlined />} loading={analyzing} onClick={handleQuickModel}>快速建模</Button>
            </Space>

            {connectionResult && (
              <Alert
                style={{ marginTop: 12 }}
                type={connectionResult.success ? 'success' : 'error'}
                message={connectionResult.success ? `连接成功 — ${connectionResult.table_count} 张表` : connectionResult.error}
                description={connectionResult.success && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {(connectionResult.tables || []).slice(0, 20).map((t) => <Tag key={t}>{t}</Tag>)}
                    {connectionResult.table_count > 20 && <Tag>+{connectionResult.table_count - 20} more</Tag>}
                  </div>
                )}
              />
            )}
          </Form>
        </Card>
      )}

      {/* Step 1: Preview */}
      {step === 1 && analysisResult && (
        <Card>
          <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between' }}>
            <Space>
              <Button onClick={() => setViewMode('list')} type={viewMode === 'list' ? 'primary' : 'default'}>列表视图</Button>
              <Button onClick={() => { setViewMode('json'); setEditingJson(JSON.stringify({ object_types: analysisResult.object_types, link_types: analysisResult.link_types, action_types: analysisResult.action_types }, null, 2)); }} type={viewMode === 'json' ? 'primary' : 'default'}>JSON 编辑</Button>
            </Space>
            <Space>
              <Button onClick={() => setStep(0)}>上一步</Button>
              <Button type="primary" onClick={handleCompile}>编译检查</Button>
            </Space>
          </div>

          {viewMode === 'list' && (
            <>
              <Title level={5}>对象类型 ({analysisResult.object_types?.length || 0})</Title>
              {analysisResult.object_types?.map((ot, i) => (
                <Card key={i} size="small" style={{ marginBottom: 8 }} title={<>{ot.display_name} <Tag>{ot.type_name}</Tag></>}>
                  <Text type="secondary">{ot.description}</Text>
                  <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {ot.properties?.map((p, j) => (
                      <Tag key={j} color={p.required ? 'red' : 'default'}>
                        {p.name}: {p.type}{p.required ? '*' : ''}
                      </Tag>
                    ))}
                  </div>
                </Card>
              ))}
              {analysisResult.link_types?.length > 0 && (
                <>
                  <Title level={5} style={{ marginTop: 16 }}>链接类型 ({analysisResult.link_types.length})</Title>
                  {analysisResult.link_types.map((lt, i) => (
                    <Tag key={i} color="blue">{lt.link_name}: {lt.source_type} → {lt.target_type}</Tag>
                  ))}
                </>
              )}
            </>
          )}

          {viewMode === 'json' && (
            <Input.TextArea rows={20} value={editingJson} onChange={(e) => setEditingJson(e.target.value)} />
          )}
        </Card>
      )}

      {/* Step 2: Compile result + confirm register */}
      {step === 2 && compileResult && (
        <Card>
          {compileResult.errors?.length > 0 && (
            <Alert type="error" message="编译错误" description={compileResult.errors.join('; ')} style={{ marginBottom: 12 }} />
          )}
          {compileResult.warnings?.length > 0 && (
            <Alert type="warning" message="警告" description={compileResult.warnings.join('; ')} style={{ marginBottom: 12 }} />
          )}
          {compileResult.valid && <Alert type="success" message="编译通过" style={{ marginBottom: 12 }} />}

          <Paragraph>统计: {compileResult.stats?.object_type_count} 个对象类型, {compileResult.stats?.link_type_count} 个链接类型, {compileResult.stats?.action_type_count} 个动作类型</Paragraph>
          <Paragraph>自动修复: {compileResult.auto_fix_count} 处</Paragraph>

          <Space>
            <Button onClick={() => setStep(1)}>上一步</Button>
            <Button type="primary" icon={<CheckCircleOutlined />} onClick={handleRegister}>注册本体 + 触发同步</Button>
          </Space>
        </Card>
      )}

      {/* Step 3: Done */}
      {step === 3 && registerResult && (
        <Card>
          <Alert type="success" message="注册完成" description={`新建 ${registerResult.created} 个类型, 合并 ${registerResult.merged} 个已有类型`} />
          <div style={{ marginTop: 16 }}>
            <Tag color="purple">新建: {registerResult.object_types?.join(', ') || '无'}</Tag>
          </div>
          <Button style={{ marginTop: 16 }} onClick={() => { setStep(0); setAnalysisResult(null); setCompileResult(null); setRegisterResult(null); }}>重新建模</Button>
        </Card>
      )}
    </div>
  );
}
