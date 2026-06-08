import { useState, useEffect, useCallback } from 'react';
import { Card, Table, Button, Space, Typography, message, Tag, Tabs, Select, Form, Input, Switch, Row, Col, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined, ReloadOutlined, SafetyOutlined } from '@ant-design/icons';
import * as acrApi from '../api/acr';
import * as ontologyApi from '../api/ontology';

const { Title, Text } = Typography;
const DATASET_ID = '_ontology_default';

export default function PermissionsPage() {
  const [activeTab, setActiveTab] = useState('overview');
  const [objects, setObjects] = useState([]);
  const [loading, setLoading] = useState(false);

  // ACR state (same pattern as ACRPage)
  const [rules, setRules] = useState([]);
  const [groups, setGroups] = useState([]);
  const [bindings, setBindings] = useState([]);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [rulesRes, groupsRes, bindingsRes] = await Promise.all([
        acrApi.listRules({ resource_type: 'ontology_type' }),
        acrApi.listRuleGroups(),
        acrApi.listBindings(),
      ]);
      if (rulesRes.code === 0) setRules(rulesRes.data?.items || rulesRes.data || []);
      if (groupsRes.code === 0) setGroups(groupsRes.data?.items || groupsRes.data || []);
      if (bindingsRes.code === 0) setBindings(bindingsRes.data?.items || bindingsRes.data || []);
    } catch { /* */ }
    setLoading(false);
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '名称', dataIndex: 'name' },
    { title: '资源类型', dataIndex: 'resource_type', width: 120, render: (v) => <Tag>{v}</Tag> },
    { title: '字段', dataIndex: 'field', width: 100 },
    { title: '运算符', dataIndex: 'operator', width: 90, render: (v) => <Tag color="blue">{v}</Tag> },
    { title: '值', dataIndex: 'value', render: (v) => <code>{JSON.stringify(v)}</code> },
    { title: '启用', dataIndex: 'enabled', width: 60, render: (v) => v ? <Tag color="green">是</Tag> : <Tag color="red">否</Tag> },
  ];

  const tabs = [
    {
      key: 'overview',
      label: '概述',
      children: (
        <Card>
          <div style={{ maxWidth: 600 }}>
            <Title level={5}>FGAC 细粒度访问控制</Title>
            <Paragraph>
              FGAC (Fine-Grained Access Control) 通过 ACR (Access Control Rules) 实现对本体资源（类型、实例等）的行级和属性级安全控制。
            </Paragraph>
            <Paragraph>
              <Text strong>当前活跃规则: </Text><Tag color="blue">{rules.length} 条</Tag>
              <Text strong style={{ marginLeft: 16 }}>规则组: </Text><Tag color="purple">{groups.length} 个</Tag>
              <Text strong style={{ marginLeft: 16 }}>绑定: </Text><Tag color="orange">{bindings.length} 个</Tag>
            </Paragraph>
            <Paragraph type="secondary">
              完整 ACR 管理请前往 <a href="/admin/acr">系统管理 → ACR 配置</a>
            </Paragraph>
          </div>
        </Card>
      ),
    },
    {
      key: 'rules',
      label: `ACR 规则 (${rules.length})`,
      children: (
        <div>
          <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: 16 }} onClick={() => window.location.href = '/admin/acr'}>
            前往管理
          </Button>
          <Table columns={columns} dataSource={rules} rowKey="id" loading={loading} size="small" />
        </div>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={4}><SafetyOutlined style={{ marginRight: 8 }} />权限管理 (FGAC)</Title>
        <Text type="secondary">本体数据集的细粒度访问控制</Text>
      </div>
      <Card><Tabs activeKey={activeTab} onChange={setActiveTab} items={tabs} /></Card>
    </div>
  );
}

function Paragraph({ children }) {
  return <div style={{ marginBottom: 8, color: '#64748b', lineHeight: 1.7 }}>{children}</div>;
}
