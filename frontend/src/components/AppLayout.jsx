import { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Avatar, Button, Dropdown, Layout, Menu, theme, Typography } from 'antd';
import {
  DashboardOutlined,
  NodeIndexOutlined,
  ApartmentOutlined,
  ThunderboltOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  RobotOutlined,
  KeyOutlined,
  ApiOutlined,
  HeartOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../stores/authStore';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '概览' },
  {
    key: 'rag', icon: <RobotOutlined />, label: 'RAG 引擎',
    children: [
      { key: '/ragflow/knowledge-base', label: '知识库管理' },
      { key: '/ragflow/chat', label: '对话助手' },
      { key: '/ragflow/retrieval', label: '内容检索' },
      { key: '/rag-evaluation', label: 'RAG 评测' },
      { key: '/ragflow/model-config', label: '模型配置' },
      { key: '/ragflow/service-config', label: '服务配置' },
    ],
  },
  {
    key: 'ontology', icon: <ApartmentOutlined />, label: 'ONTOLOGY',
    children: [
      { key: '/ontology/graph', label: '本体图谱' },
      { key: '/ontology/types', label: '类型定义' },
      { key: '/ontology/instances', label: '实例管理' },
      {
        key: 'data-mgmt', label: '数据管理',
        children: [
          { key: '/ontology/modeling', label: 'LLM 建模' },
          { key: '/ontology/quick-modeling', label: '快速建模' },
          { key: '/ontology/structure-changes', label: '结构变更' },
          { key: '/ontology/data-sync', label: '数据同步' },
        ],
      },
      { key: '/ontology/versions', label: '版本管理' },
      { key: '/ontology/permissions', label: '权限管理(FGAC)' },
    ],
  },
  {
    key: 'graphrag', icon: <NodeIndexOutlined />, label: 'GRAPHRAG',
    children: [
      { key: '/graphrag/knowledge-base', label: '知识库' },
      { key: '/graphrag/documents', label: '文档处理' },
      { key: '/graphrag/graph', label: '知识图谱' },
      { key: '/graphrag/qa', label: '知识问答' },
      { key: '/graphrag/model-config', label: '模型配置' },
    ],
  },
  { key: '/skills', icon: <ThunderboltOutlined />, label: 'SKILLS 管理' },
  {
    key: 'admin', icon: <SettingOutlined />, label: '系统管理',
    children: [
      { key: '/admin/users', label: '用户管理' },
      { key: '/admin/roles', label: '角色管理' },
      { key: '/admin/groups', label: '用户组管理' },
      { key: '/admin/tokens', label: '令牌管理' },
      { key: '/admin/acr', label: 'ACR 配置' },
      { key: '/admin/system-config', label: '系统配置' },
    ],
  },
  { key: '/api-keys', icon: <KeyOutlined />, label: 'API 接口' },
  { key: '/personal-tokens', icon: <ApiOutlined />, label: '个人令牌' },
];

function findOpenKeys(pathname) {
  const openKeys = [];
  for (const item of menuItems) {
    if (item.children) {
      const found = item.children.some((c) => pathname.startsWith(c.key) || (c.children && c.children.some((cc) => pathname.startsWith(cc.key))));
      if (found) openKeys.push(item.key);
    }
  }
  return openKeys;
}

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { token: { colorBgContainer } } = theme.useToken();

  const handleMenuClick = ({ key }) => navigate(key);

  const userMenu = {
    items: [
      { key: 'profile', icon: <UserOutlined />, label: '个人中心' },
      { key: 'health', icon: <HeartOutlined />, label: '健康检查' },
      { key: 'api-keys', icon: <ApiOutlined />, label: 'API Key' },
      { type: 'divider' },
      { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
    ],
    onClick: ({ key }) => {
      if (key === 'logout') logout();
      else if (key === 'profile') navigate('/profile');
      else if (key === 'health') navigate('/health');
      else if (key === 'api-keys') navigate('/api-keys');
    },
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={240}
        style={{ background: colorBgContainer, borderRight: '1px solid #e8e8e8' }}
      >
        <div style={styles.logo}>
          {collapsed ? '♦' : '♦ OntologyReady 2.0'}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          defaultOpenKeys={findOpenKeys(location.pathname)}
          onClick={handleMenuClick}
          items={menuItems}
          style={{ borderInlineEnd: 'none' }}
        />
      </Sider>
      <Layout>
        <Header style={{ background: colorBgContainer, padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
          <Dropdown menu={userMenu}>
            <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Avatar icon={<UserOutlined />} style={{ background: '#7c3aed' }} />
              <Text>{user?.full_name || user?.username || '用户'}</Text>
            </div>
          </Dropdown>
        </Header>
        <Content style={{ margin: 0, overflow: 'auto' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}

const styles = {
  logo: { height: 48, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, fontWeight: 700, color: '#7c3aed', borderBottom: '1px solid #f0f0f0' },
};
