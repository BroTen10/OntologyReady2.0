import { useState, useEffect, useCallback } from 'react';
import { Tabs, Table, Button, Modal, Form, Input, Select, Switch, Space, Popconfirm, Card, message, Row, Col, InputNumber, Tag, Tooltip } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ApartmentOutlined, LinkOutlined, ThunderboltOutlined } from '@ant-design/icons';
import * as ontologyApi from '../api/ontology';

const PROP_TYPES = [
  { value: 'string', label: 'string' },
  { value: 'number', label: 'number' },
  { value: 'datetime', label: 'datetime' },
  { value: 'boolean', label: 'boolean' },
];

const DATASET_ID = '_ontology_default';

export default function TypesPage() {
  const [activeTab, setActiveTab] = useState('object');
  const [objects, setObjects] = useState([]);
  const [links, setLinks] = useState([]);
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [oRes, lRes, aRes] = await Promise.all([
        ontologyApi.listObjectTypes(DATASET_ID),
        ontologyApi.listLinkTypes(DATASET_ID),
        ontologyApi.listActionTypes(DATASET_ID),
      ]);
      if (oRes.code === 0) setObjects(oRes.data?.items || oRes.data || []);
      if (lRes.code === 0) setLinks(lRes.data?.items || lRes.data || []);
      if (aRes.code === 0) setActions(aRes.data?.items || aRes.data || []);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const openModal = (type, record = null) => {
    setEditing(record ? { ...record, _type: type } : { _type: type });
    if (record) {
      form.setFieldsValue(record);
    } else {
      form.resetFields();
      form.setFieldsValue({ _type: type });
    }
    setModalOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    const type = values._type;
    delete values._type;
    setSaving(true);
    try {
      let res;
      if (type === 'object') {
        if (editing?.name) {
          res = await ontologyApi.updateObjectType(DATASET_ID, editing.name, values);
        } else {
          res = await ontologyApi.createObjectType(DATASET_ID, values);
        }
      } else if (type === 'link') {
        if (editing?.name) {
          res = await ontologyApi.updateLinkType(DATASET_ID, editing.name, values);
        } else {
          res = await ontologyApi.createLinkType(DATASET_ID, values);
        }
      } else {
        if (editing?.name) {
          res = await ontologyApi.updateActionType(DATASET_ID, editing.name, values);
        } else {
          res = await ontologyApi.createActionType(DATASET_ID, values);
        }
      }
      if (res.code === 0) {
        message.success(editing?.name ? '已更新' : '已创建');
        setModalOpen(false);
        fetchAll();
      }
    } finally { setSaving(false); }
  };

  const handleDelete = async (type, name) => {
    let res;
    if (type === 'object') res = await ontologyApi.deleteObjectType(DATASET_ID, name);
    else if (type === 'link') res = await ontologyApi.deleteLinkType(DATASET_ID, name);
    else res = await ontologyApi.deleteActionType(DATASET_ID, name);
    if (res.code === 0) { message.success('已删除'); fetchAll(); }
  };

  const objectColumns = [
    { title: '类型名', dataIndex: 'name', key: 'name', render: (v) => <Text code strong>{v}</Text> },
    { title: '显示名', dataIndex: 'display_name', key: 'display' },
    { title: '属性', dataIndex: 'properties', key: 'props', render: (props) => (
      <Space wrap size={[0, 4]}>
        {(props || []).map((p, i) => (
          <Tooltip key={i} title={`${p.type}${p.required ? ' (必填)' : ''}${p.unique ? ' (唯一)' : ''}`}>
            <Tag color={p.required ? 'blue' : 'default'}>{p.name}</Tag>
          </Tooltip>
        ))}
      </Space>
    )},
    {
      title: '操作', key: 'actions', width: 120,
      render: (_, r) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openModal('object', r)} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete('object', r.name)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const linkColumns = [
    { title: '关系名', dataIndex: 'name', key: 'name', render: (v) => <Text code strong>{v}</Text> },
    { title: '显示名', dataIndex: 'display_name', key: 'display' },
    { title: '源类型', dataIndex: 'source_type', key: 'src', render: (v) => <Tag color="green">{v}</Tag> },
    { title: '目标类型', dataIndex: 'target_type', key: 'tgt', render: (v) => <Tag color="orange">{v}</Tag> },
    { title: '有向', dataIndex: 'directed', key: 'dir', width: 60, render: (v) => v !== false ? <Tag color="purple">是</Tag> : <Tag>否</Tag> },
    {
      title: '操作', key: 'actions', width: 120,
      render: (_, r) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openModal('link', r)} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete('link', r.name)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const actionColumns = [
    { title: '操作名', dataIndex: 'name', key: 'name', render: (v) => <Text code strong>{v}</Text> },
    { title: '显示名', dataIndex: 'display_name', key: 'display' },
    { title: 'Webhook URL', dataIndex: 'webhook_url', key: 'url', ellipsis: true, render: (v) => v || '-' },
    { title: 'HTTP 方法', dataIndex: 'method', key: 'method', width: 90, render: (v) => v ? <Tag>{v}</Tag> : '-' },
    { title: '影响类型', dataIndex: 'effect_type', key: 'effect', width: 100, render: (v) => v || '-' },
    {
      title: '操作', key: 'actions', width: 120,
      render: (_, r) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openModal('action', r)} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete('action', r.name)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const tabs = [
    { key: 'object', icon: <ApartmentOutlined />, label: `Object Types (${objects.length})`, children: (
      <div>
        <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: 16 }} onClick={() => openModal('object')}>新建 Object Type</Button>
        <Table columns={objectColumns} dataSource={objects} rowKey="name" loading={loading} size="small" />
      </div>
    )},
    { key: 'link', icon: <LinkOutlined />, label: `Link Types (${links.length})`, children: (
      <div>
        <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: 16 }} onClick={() => openModal('link')}>新建 Link Type</Button>
        <Table columns={linkColumns} dataSource={links} rowKey="name" loading={loading} size="small" />
      </div>
    )},
    { key: 'action', icon: <ThunderboltOutlined />, label: `Action Types (${actions.length})`, children: (
      <div>
        <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: 16 }} onClick={() => openModal('action')}>新建 Action Type</Button>
        <Table columns={actionColumns} dataSource={actions} rowKey="name" loading={loading} size="small" />
      </div>
    )},
  ];

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>类型定义</h1>
      <Card><Tabs activeKey={activeTab} onChange={setActiveTab} items={tabs} /></Card>

      <Modal
        title={editing?.name ? `编辑 ${editing._type} type` : `新建 ${form.getFieldValue('_type') || ''} type`}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        width={700}
      >
        <Form form={form} layout="vertical" initialValues={{ directed: true }}>
          <Form.Item name="_type" hidden><Input /></Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="名称" rules={[{ required: true }]}>
                <Input placeholder="唯一标识名 (英文)" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="display_name" label="显示名">
                <Input placeholder="中文显示名" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item noStyle shouldUpdate={(prev, cur) => prev._type !== cur._type}>
            {({ getFieldValue }) => {
              const t = getFieldValue('_type');
              if (t === 'link') return (
                <Row gutter={16}>
                  <Col span={8}><Form.Item name="source_type" label="源类型" rules={[{ required: true }]}><Input /></Form.Item></Col>
                  <Col span={8}><Form.Item name="target_type" label="目标类型" rules={[{ required: true }]}><Input /></Form.Item></Col>
                  <Col span={8}><Form.Item name="directed" label="有向" valuePropName="checked"><Switch /></Form.Item></Col>
                </Row>
              );
              if (t === 'action') return (
                <>
                  <Form.Item name="webhook_url" label="Webhook URL"><Input placeholder="https://..." /></Form.Item>
                  <Row gutter={16}>
                    <Col span={8}><Form.Item name="method" label="HTTP Method"><Select options={['GET','POST','PUT','DELETE'].map(v=>({value:v,label:v}))} /></Form.Item></Col>
                    <Col span={8}><Form.Item name="effect_type" label="Effect Type"><Input /></Form.Item></Col>
                  </Row>
                </>
              );
              return null;
            }}
          </Form.Item>

          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(prev, cur) => prev._type !== cur._type}>
            {({ getFieldValue }) => {
              if (getFieldValue('_type') !== 'object') return null;
              return (
                <Form.List name="properties">
                  {(fields, { add, remove }) => (
                    <div>
                      <div style={{ fontWeight: 600, marginBottom: 8 }}>属性定义</div>
                      {fields.map(({ key, name, ...rest }) => (
                        <Row gutter={8} key={key} align="middle" style={{ marginBottom: 8 }}>
                          <Col span={5}><Form.Item {...rest} name={[name, 'name']} noStyle><Input placeholder="属性名" size="small" /></Form.Item></Col>
                          <Col span={4}><Form.Item {...rest} name={[name, 'type']} noStyle><Select options={PROP_TYPES} placeholder="类型" size="small" /></Form.Item></Col>
                          <Col span={3}><Form.Item {...rest} name={[name, 'required']} valuePropName="checked" noStyle><Switch size="small" /> <Text style={{fontSize:12}}>必填</Text></Form.Item></Col>
                          <Col span={3}><Form.Item {...rest} name={[name, 'unique']} valuePropName="checked" noStyle><Switch size="small" /> <Text style={{fontSize:12}}>唯一</Text></Form.Item></Col>
                          <Col span={3}><Form.Item {...rest} name={[name, 'indexed']} valuePropName="checked" noStyle><Switch size="small" /> <Text style={{fontSize:12}}>索引</Text></Form.Item></Col>
                          <Col span={2}><Button size="small" danger onClick={() => remove(name)}>删</Button></Col>
                        </Row>
                      ))}
                      <Button type="dashed" size="small" onClick={() => add({ type: 'string' })} block>+ 添加属性</Button>
                    </div>
                  )}
                </Form.List>
              );
            }}
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
