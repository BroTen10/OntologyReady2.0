import { useState, useEffect } from 'react';
import { Card, Descriptions, Tag, Typography, Spin, Alert, Button, Space, message } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, ReloadOutlined, HeartOutlined } from '@ant-design/icons';
import { getHealth } from '../api/system';

const { Title, Text } = Typography;

export default function HealthPage() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const res = await getHealth();
      if (res.code === 0) setHealth(res.data);
    } catch { message.error('健康检查失败'); }
    setLoading(false);
  };

  useEffect(() => { fetchHealth(); }, []);

  return (
    <div style={{ padding: 24, maxWidth: 700 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={4} style={{ margin: 0 }}><HeartOutlined style={{ marginRight: 8 }} />健康检查</Title>
        <Button icon={<ReloadOutlined />} onClick={fetchHealth} loading={loading}>刷新</Button>
      </div>

      {loading ? <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div> :
        health ? (
          <Card>
            <Alert
              type={health.status === 'ok' || health.status === 'healthy' ? 'success' : 'error'}
              message={`服务状态: ${health.status || 'unknown'}`}
              showIcon
              icon={health.status === 'ok' || health.status === 'healthy' ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
              style={{ marginBottom: 20 }}
            />
            <Descriptions bordered column={1} size="small">
              {Object.entries(health).map(([k, v]) => (
                <Descriptions.Item key={k} label={k}>
                  {typeof v === 'boolean' ? (
                    v ? <Tag color="green">true</Tag> : <Tag color="red">false</Tag>
                  ) : typeof v === 'object' ? (
                    <code style={{ fontSize: 12 }}>{JSON.stringify(v)}</code>
                  ) : (
                    <Text>{String(v)}</Text>
                  )}
                </Descriptions.Item>
              ))}
            </Descriptions>
          </Card>
        ) : (
          <Alert type="error" message="无法获取健康状态" showIcon />
        )
      }
    </div>
  );
}
