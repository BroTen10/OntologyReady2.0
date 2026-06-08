import { useState, useCallback } from 'react';
import { Card, Button, Input, Space, Typography, message, Table, Tag, Empty } from 'antd';
import { SearchOutlined, FileTextOutlined } from '@ant-design/icons';
import { search } from '../api/rag';

const { Title, Text } = Typography;

export default function RetrievalPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [kbId, setKbId] = useState('');

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await search(kbId || undefined, query.trim(), 10);
      if (res.code === 0) setResults(res.data?.items || res.data || []);
    } catch { message.error('检索失败'); }
    setLoading(false);
  };

  const columns = [
    { title: '排名', dataIndex: 'rank', key: 'rank', width: 60, render: (_, __, i) => <Text strong>{i + 1}</Text> },
    { title: '文档', dataIndex: 'doc_id', key: 'doc', width: 150, render: (v) => <Text code style={{fontSize:12}}>{v}</Text> },
    { title: '内容', dataIndex: 'content', key: 'content', render: (v) => <Paragraph ellipsis={{rows:2}}>{v}</Paragraph> },
    { title: '相关度', dataIndex: 'score', key: 'score', width: 90, render: (v) => (
      <Tag color={v > 0.8 ? 'green' : v > 0.5 ? 'blue' : 'orange'}>{(v * 100).toFixed(1)}%</Tag>
    )},
    { title: '引用', dataIndex: 'metadata', key: 'meta', width: 200, render: (m) => m ? (
      <Text style={{fontSize:12}} type="secondary">{m.source || m.filename || ''}</Text>
    ) : null },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={4}><FileTextOutlined style={{ marginRight: 8 }} />内容检索</Title>
        <Text type="secondary">基于语义的全文检索，查询相关文档片段</Text>
      </div>

      <Card>
        <Space style={{ marginBottom: 16, width: '100%' }} direction="vertical">
          <Space>
            <Input placeholder="知识库 ID (可选)" value={kbId} onChange={(e) => setKbId(e.target.value)} style={{ width: 220 }} allowClear />
            <Input.Search
              prefix={<SearchOutlined />}
              placeholder="输入检索内容..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onSearch={handleSearch}
              enterButton="检索"
              style={{ width: 480 }}
              loading={loading}
            />
          </Space>
        </Space>

        <Table
          columns={columns}
          dataSource={results}
          rowKey={(_, i) => i}
          loading={loading}
          pagination={false}
          locale={{ emptyText: <Empty description={query ? '未找到匹配结果' : '输入关键词开始检索'} /> }}
        />
      </Card>
    </div>
  );
}

function Paragraph({ children, ellipsis }) {
  const t = children || '';
  const [expanded, setExpanded] = useState(false);
  if (!ellipsis || t.length < 200) return <div>{t}</div>;
  const short = t.slice(0, 200);
  return (
    <div>
      {expanded ? t : short + '...'}
      <Button type="link" size="small" onClick={() => setExpanded(!expanded)} style={{padding:0}}>
        {expanded ? '收起' : '展开'}
      </Button>
    </div>
  );
}
