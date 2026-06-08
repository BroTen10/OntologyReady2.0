import { useState, useEffect, useCallback } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, Select, Switch, Tag, Space, Popconfirm,
  Tabs, message, Row, Col, InputNumber,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, LinkOutlined } from '@ant-design/icons';
import * as acrApi from '../api/acr';

const OPERATORS = [
  { value: 'eq', label: '等于 (eq)' },
  { value: 'ne', label: '不等于 (ne)' },
  { value: 'in', label: '包含于 (in)' },
  { value: 'not_in', label: '不包含于 (not_in)' },
  { value: 'intersects', label: '交集 (intersects)' },
  { value: 'contains', label: '包含 (contains)' },
  { value: 'gt', label: '大于 (gt)' },
  { value: 'gte', label: '大于等于 (gte)' },
  { value: 'lt', label: '小于 (lt)' },
  { value: 'lte', label: '小于等于 (lte)' },
];

const USER_ATTRS = [
  { value: 'user:user_id', label: 'user_id' },
  { value: 'user:username', label: 'username' },
  { value: 'user:email', label: 'email' },
  { value: 'user:roles', label: 'roles (list)' },
  { value: 'user:groups', label: 'groups (list)' },
  { value: 'user:custom:department', label: 'custom:department' },
];

const RESOURCE_TYPES = [
  { value: 'dataset', label: 'Dataset' },
  { value: 'ontology_type', label: 'Ontology Type' },
  { value: 'instance', label: 'Instance' },
  { value: 'rag_kb', label: 'RAG KB' },
  { value: 'graphrag_kb', label: 'GraphRAG KB' },
];

export default function ACRPage() {
  const [activeTab, setActiveTab] = useState('config');
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState(null);
  const [rules, setRules] = useState([]);
  const [groups, setGroups] = useState([]);
  const [bindings, setBindings] = useState([]);

  // Config form
  const [configForm] = Form.useForm();
  const [configEditing, setConfigEditing] = useState(false);

  // Rule modal
  const [ruleModalOpen, setRuleModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [ruleForm] = Form.useForm();
  const [ruleSaving, setRuleSaving] = useState(false);

  // Group modal
  const [groupModalOpen, setGroupModalOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState(null);
  const [groupForm] = Form.useForm();
  const [groupSaving, setGroupSaving] = useState(false);

  // Binding modal
  const [bindingModalOpen, setBindingModalOpen] = useState(false);
  const [bindingForm] = Form.useForm();
  const [bindingSaving, setBindingSaving] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [configRes, rulesRes, groupsRes, bindingsRes] = await Promise.all([
        acrApi.getACRConfig(),
        acrApi.listRules(),
        acrApi.listRuleGroups(),
        acrApi.listBindings(),
      ]);
      if (configRes.code === 0) setConfig(configRes.data);
      if (rulesRes.code === 0) setRules(rulesRes.data);
      if (groupsRes.code === 0) setGroups(groupsRes.data);
      if (bindingsRes.code === 0) setBindings(bindingsRes.data);
    } catch (e) {
      message.error('加载数据失败');
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // ── Config handlers ──────────────────────────────────────

  const handleConfigEdit = () => {
    configForm.setFieldsValue(config);
    setConfigEditing(true);
  };

  const handleConfigSave = async () => {
    const values = configForm.getFieldsValue();
    const res = await acrApi.updateACRConfig(values);
    if (res.code === 0) {
      setConfig(res.data);
      setConfigEditing(false);
      message.success('ACR 配置已更新');
    }
  };

  // ── Rule handlers ────────────────────────────────────────

  const openRuleModal = (rule) => {
    if (rule) {
      setEditingRule(rule);
      ruleForm.setFieldsValue(rule);
    } else {
      setEditingRule(null);
      ruleForm.resetFields();
    }
    setRuleModalOpen(true);
  };

  const handleRuleSave = async () => {
    const values = await ruleForm.validateFields();
    setRuleSaving(true);
    try {
      let res;
      if (editingRule) {
        res = await acrApi.updateRule(editingRule.id, values);
      } else {
        res = await acrApi.createRule(values);
      }
      if (res.code === 0) {
        message.success(editingRule ? '规则已更新' : '规则已创建');
        setRuleModalOpen(false);
        fetchAll();
      }
    } finally {
      setRuleSaving(false);
    }
  };

  const handleDeleteRule = async (id) => {
    const res = await acrApi.deleteRule(id);
    if (res.code === 0) {
      message.success('规则已删除');
      fetchAll();
    }
  };

  // ── Group handlers ───────────────────────────────────────

  const openGroupModal = (group) => {
    if (group) {
      setEditingGroup(group);
      groupForm.setFieldsValue(group);
    } else {
      setEditingGroup(null);
      groupForm.resetFields();
    }
    setGroupModalOpen(true);
  };

  const handleGroupSave = async () => {
    const values = await groupForm.validateFields();
    setGroupSaving(true);
    try {
      let res;
      if (editingGroup) {
        res = await acrApi.updateRuleGroup(editingGroup.id, values);
      } else {
        res = await acrApi.createRuleGroup(values);
      }
      if (res.code === 0) {
        message.success(editingGroup ? '规则组已更新' : '规则组已创建');
        setGroupModalOpen(false);
        fetchAll();
      }
    } finally {
      setGroupSaving(false);
    }
  };

  const handleDeleteGroup = async (id) => {
    const res = await acrApi.deleteRuleGroup(id);
    if (res.code === 0) {
      message.success('规则组已删除');
      fetchAll();
    }
  };

  // ── Binding handlers ─────────────────────────────────────

  const openBindingModal = () => {
    bindingForm.resetFields();
    setBindingModalOpen(true);
  };

  const handleBindingSave = async () => {
    const values = await bindingForm.validateFields();
    setBindingSaving(true);
    try {
      const res = await acrApi.createBinding(values);
      if (res.code === 0) {
        message.success('绑定已创建');
        setBindingModalOpen(false);
        fetchAll();
      }
    } finally {
      setBindingSaving(false);
    }
  };

  const handleDeleteBinding = async (id) => {
    const res = await acrApi.deleteBinding(id);
    if (res.code === 0) {
      message.success('绑定已删除');
      fetchAll();
    }
  };

  // ── Table columns ────────────────────────────────────────

  const ruleColumns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '名称', dataIndex: 'name', width: 150 },
    { title: '资源类型', dataIndex: 'resource_type', width: 130, render: v => <Tag>{v}</Tag> },
    { title: '字段', dataIndex: 'field', width: 130 },
    { title: '运算符', dataIndex: 'operator', width: 100, render: v => <Tag color="blue">{v}</Tag> },
    { title: '值', dataIndex: 'value', width: 160, render: v => <code>{JSON.stringify(v)}</code> },
    { title: '优先级', dataIndex: 'priority', width: 70 },
    {
      title: '启用', dataIndex: 'enabled', width: 70,
      render: v => v ? <Tag color="green">是</Tag> : <Tag color="red">否</Tag>,
    },
    {
      title: '操作', key: 'actions', width: 120,
      render: (_, r) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openRuleModal(r)} />
          <Popconfirm title="确认删除?" onConfirm={() => handleDeleteRule(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const groupColumns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '名称', dataIndex: 'name', width: 150 },
    { title: '显示名', dataIndex: 'display_name', width: 150 },
    { title: '规则ID', dataIndex: 'rule_ids', width: 180, render: v => v?.join(', ') || '-' },
    { title: '逻辑', dataIndex: 'logic', width: 70, render: v => <Tag color="purple">{v}</Tag> },
    {
      title: '操作', key: 'actions', width: 120,
      render: (_, g) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openGroupModal(g)} />
          <Popconfirm title="确认删除?" onConfirm={() => handleDeleteGroup(g.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const bindingColumns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '规则组ID', dataIndex: 'rule_group_id', width: 100 },
    { title: '用户ID', dataIndex: 'user_id', width: 300, render: v => v || '-' },
    { title: '组名', dataIndex: 'group_name', width: 150, render: v => v ? <Tag>{v}</Tag> : '-' },
    {
      title: '操作', key: 'actions', width: 80,
      render: (_, b) => (
        <Popconfirm title="确认删除?" onConfirm={() => handleDeleteBinding(b.id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  // ── Tab items ────────────────────────────────────────────

  const tabItems = [
    {
      key: 'config',
      label: 'ACR 配置',
      children: (
        <Card loading={loading}>
          {config && !configEditing ? (
            <div>
              <Row gutter={[16, 16]}>
                {Object.entries(config).map(([k, v]) => (
                  <Col span={8} key={k}>
                    <Card size="small" title={k}>
                      {typeof v === 'boolean' ? (
                        v ? <Tag color="green">true</Tag> : <Tag color="red">false</Tag>
                      ) : (
                        <code>{JSON.stringify(v)}</code>
                      )}
                    </Card>
                  </Col>
                ))}
              </Row>
              <Button type="primary" style={{ marginTop: 16 }} onClick={handleConfigEdit}>
                编辑配置
              </Button>
            </div>
          ) : null}
          {configEditing && (
            <Form form={configForm} layout="vertical">
              <Row gutter={16}>
                {['acr_enabled', 'row_level_security', 'property_level_security', 'userid_injection', 'admin_bypass', 'public_data_allowed'].map(k => (
                  <Col span={8} key={k}>
                    <Form.Item name={k} label={k} valuePropName="checked">
                      <Switch />
                    </Form.Item>
                  </Col>
                ))}
              </Row>
              <Form.Item name="admin_roles" label="admin_roles">
                <Select mode="tags" placeholder="Admin roles" />
              </Form.Item>
              <Space>
                <Button type="primary" onClick={handleConfigSave}>保存</Button>
                <Button onClick={() => setConfigEditing(false)}>取消</Button>
              </Space>
            </Form>
          )}
        </Card>
      ),
    },
    {
      key: 'rules',
      label: `访问规则 (${rules.length})`,
      children: (
        <div>
          <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: 16 }} onClick={() => openRuleModal(null)}>
            新建规则
          </Button>
          <Table columns={ruleColumns} dataSource={rules} rowKey="id" loading={loading} size="small" />
        </div>
      ),
    },
    {
      key: 'groups',
      label: `规则组 (${groups.length})`,
      children: (
        <div>
          <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: 16 }} onClick={() => openGroupModal(null)}>
            新建规则组
          </Button>
          <Table columns={groupColumns} dataSource={groups} rowKey="id" loading={loading} size="small" />
        </div>
      ),
    },
    {
      key: 'bindings',
      label: `绑定 (${bindings.length})`,
      children: (
        <div>
          <Button type="primary" icon={<LinkOutlined />} style={{ marginBottom: 16 }} onClick={openBindingModal}>
            新建绑定
          </Button>
          <Table columns={bindingColumns} dataSource={bindings} rowKey="id" loading={loading} size="small" />
        </div>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>ACR 细粒度权限管控</h1>
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />

      {/* Rule Modal */}
      <Modal
        title={editingRule ? '编辑规则' : '新建规则'}
        open={ruleModalOpen}
        onOk={handleRuleSave}
        onCancel={() => setRuleModalOpen(false)}
        confirmLoading={ruleSaving}
        width={640}
      >
        <Form form={ruleForm} layout="vertical" initialValues={{ operator: 'eq', priority: 0, enabled: true }}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="resource_type" label="资源类型" rules={[{ required: true }]}>
                <Select options={RESOURCE_TYPES} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="field" label="字段" rules={[{ required: true }]}>
                <Input placeholder="如 owner_id, dataset_id" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="operator" label="运算符" rules={[{ required: true }]}>
                <Select options={OPERATORS} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="value" label="值 (静态值或用户属性)" rules={[{ required: true }]}>
                <Select mode="combobox" options={USER_ATTRS} placeholder="值或 user:xxx 引用" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="priority" label="优先级">
                <InputNumber min={0} max={999} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* Group Modal */}
      <Modal
        title={editingGroup ? '编辑规则组' : '新建规则组'}
        open={groupModalOpen}
        onOk={handleGroupSave}
        onCancel={() => setGroupModalOpen(false)}
        confirmLoading={groupSaving}
      >
        <Form form={groupForm} layout="vertical" initialValues={{ logic: 'and' }}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="display_name" label="显示名">
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="rule_ids" label="规则ID列表">
            <Select mode="tags" placeholder="输入规则 ID (用回车分隔)" />
          </Form.Item>
          <Form.Item name="logic" label="组合逻辑">
            <Select options={[{ value: 'and', label: 'AND' }, { value: 'or', label: 'OR' }]} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Binding Modal */}
      <Modal
        title="新建绑定"
        open={bindingModalOpen}
        onOk={handleBindingSave}
        onCancel={() => setBindingModalOpen(false)}
        confirmLoading={bindingSaving}
      >
        <Form form={bindingForm} layout="vertical">
          <Form.Item name="rule_group_id" label="规则组 ID" rules={[{ required: true }]}>
            <Select
              options={groups.map(g => ({ value: g.id, label: `${g.name} (ID: ${g.id})` }))}
              placeholder="选择规则组"
            />
          </Form.Item>
          <Form.Item name="user_id" label="用户 ID (与组名二选一或两者都填)">
            <Input placeholder="UUID 格式的用户 ID" />
          </Form.Item>
          <Form.Item name="group_name" label="组名 (与用户ID二选一或两者都填)">
            <Input placeholder="如 admins, developers" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
