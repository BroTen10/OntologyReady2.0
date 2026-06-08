import { useState, useEffect, useCallback } from 'react';
import { Card, Button, Space, Typography, Menu } from 'antd';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import {
  DatabaseOutlined, ApiOutlined, SyncOutlined, BranchesOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

const subNav = [
  { key: '/ontology/modeling', icon: <ApiOutlined />, label: 'LLM 建模' },
  { key: '/ontology/quick-modeling', icon: <DatabaseOutlined />, label: '快速建模' },
  { key: '/ontology/structure-changes', icon: <SyncOutlined />, label: '结构变更' },
  { key: '/ontology/data-sync', icon: <BranchesOutlined />, label: '数据同步' },
];

export default function DataManagementPage() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={4}>数据管理</Title>
        <Text type="secondary">数据集的数据建模、结构变更检测与多源数据同步</Text>
      </div>
      <Card>
        <Menu
          mode="horizontal"
          selectedKeys={[location.pathname]}
          onClick={({ key }) => navigate(key)}
          items={subNav}
          style={{ marginBottom: 24 }}
        />
        <div style={{ padding: '0 0' }}>
          <Outlet />
        </div>
      </Card>
    </div>
  );
}
