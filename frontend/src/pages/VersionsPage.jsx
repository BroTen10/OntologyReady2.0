import { useState, useEffect, useCallback } from 'react';
import {
  Table, Button, Tag, Space, Modal, Descriptions, Typography, message, Popconfirm,
  Card, List, Spin, Empty, Badge, Timeline, Tooltip, Input, Select, Alert,
} from 'antd';
import {
  RollbackOutlined, DiffOutlined, EyeOutlined, EditOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import api from '../api/client';
import { listVersions, getVersion, diffVersions, rollbackVersion, updateVersionNotes } from '../api/versioning';

const { Text, Title } = Typography;
const { TextArea } = Input;

const ENTITY_LABELS = {
  object_type: '对象类型',
  link_type: '链接类型',
  action_type: '动作类型',
};

export default function VersionsPage() {
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [datasetsLoading, setDatasetsLoading] = useState(true);

  const [versions, setVersions] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);

  // Modals
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailVersion, setDetailVersion] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [diffOpen, setDiffOpen] = useState(false);
  const [diffs, setDiffs] = useState([]);
  const [diffLoading, setDiffLoading] = useState(false);

  const [notesOpen, setNotesOpen] = useState(false);
  const [notesVersion, setNotesVersion] = useState(null);
  const [notesText, setNotesText] = useState('');
  const [notesSaving, setNotesSaving] = useState(false);

  // Load datasets
  useEffect(() => {
    (async () => {
      setDatasetsLoading(true);
      try {
        const res = await api.get('/datasets', { params: { page_size: 100 } });
        if (res.data?.code === 0) {
          const items = res.data.data?.items || [];
          setDatasets(items);
          if (items.length > 0) {
            setSelectedDataset(items[0].id);
          }
        }
      } catch {
        // Datasets not available
      } finally {
        setDatasetsLoading(false);
      }
    })();
  }, []);

  const fetchVersions = useCallback(async () => {
    if (!selectedDataset) return;
    setLoading(true);
    try {
      const res = await listVersions(selectedDataset, page, 20);
      if (res.code === 0) {
        setVersions(res.data?.items || []);
        setTotal(res.data?.page_info?.total || 0);
      }
    } catch {
      // No versions yet
    } finally {
      setLoading(false);
    }
  }, [selectedDataset, page]);

  useEffect(() => {
    fetchVersions();
  }, [fetchVersions]);

  const handleViewDetail = async (versionId) => {
    if (!selectedDataset) return;
    setDetailLoading(true);
    setDetailOpen(true);
    setDetailVersion(null);
    try {
      const res = await getVersion(selectedDataset, versionId);
      if (res.code === 0) {
        setDetailVersion(res.data);
      }
    } finally {
      setDetailLoading(false);
    }
  };

  const handleDiff = async (versionIdA, versionIdB) => {
    if (!selectedDataset) return;
    setDiffLoading(true);
    setDiffOpen(true);
    setDiffs([]);
    try {
      const res = await diffVersions(selectedDataset, versionIdA, versionIdB);
      if (res.code === 0) {
        setDiffs(res.data?.diffs || []);
      }
    } finally {
      setDiffLoading(false);
    }
  };

  const handleRollback = async (versionId) => {
    if (!selectedDataset) return;
    try {
      const res = await rollbackVersion(selectedDataset, versionId);
      if (res.code === 0) {
        message.success(res.message || '回滚成功');
        fetchVersions();
      } else {
        message.error(res.message || '回滚失败');
      }
    } catch {
      message.error('回滚请求失败');
    }
  };

  const handleEditNotes = async () => {
    if (!selectedDataset || !notesVersion) return;
    setNotesSaving(true);
    try {
      const res = await updateVersionNotes(selectedDataset, notesVersion.version_id, notesText);
      if (res.code === 0) {
        message.success('备注已更新');
        setNotesOpen(false);
        fetchVersions();
      }
    } finally {
      setNotesSaving(false);
    }
  };

  const openNotesModal = (version) => {
    setNotesVersion(version);
    setNotesText(version.notes || '');
    setNotesOpen(true);
  };

  const columns = [
    {
      title: '#',
      dataIndex: 'version_number',
      key: 'version_number',
      width: 70,
      render: (n) => <Badge count={n} style={{ backgroundColor: '#7c3aed' }} />,
    },
    {
      title: '提交信息',
      dataIndex: 'commit_message',
      key: 'commit_message',
      ellipsis: true,
      render: (text, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{text}</Text>
          {record.notes && <Text type="secondary" style={{ fontSize: 12 }}>{record.notes}</Text>}
        </Space>
      ),
    },
    {
      title: '变更摘要',
      dataIndex: 'changes_summary',
      key: 'changes_summary',
      width: 320,
      render: (items) => (
        <Space wrap size={[4, 4]}>
          {(items || []).map((c, i) => (
            <Tag key={i} color={
              c.change_type === 'create' ? 'green' :
              c.change_type === 'delete' ? 'red' : 'blue'
            }>
              {ENTITY_LABELS[c.entity_type] || c.entity_type}: {c.entity_name} ({c.change_type === 'create' ? '创建' : c.change_type === 'update' ? '更新' : '删除'})
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '创建者',
      dataIndex: 'created_by',
      key: 'created_by',
      width: 100,
      render: (v) => v || '-',
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (v) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 240,
      render: (_, record, idx) => (
        <Space>
          <Tooltip title="查看详情">
            <Button size="small" icon={<EyeOutlined />} onClick={() => handleViewDetail(record.version_id)} />
          </Tooltip>
          <Tooltip title="对比上一版本">
            <Button
              size="small"
              icon={<DiffOutlined />}
              onClick={() => {
                const prev = versions.find(v => v.version_number === record.version_number - 1);
                if (prev) handleDiff(prev.version_id, record.version_id);
                else message.warning('没有可对比的上一个版本');
              }}
            />
          </Tooltip>
          <Tooltip title="编辑备注">
            <Button size="small" icon={<EditOutlined />} onClick={() => openNotesModal(record)} />
          </Tooltip>
          <Popconfirm
            title="确定回滚到此版本？"
            description="当前本体定义将被此版本的快照完全替换。"
            onConfirm={() => handleRollback(record.version_id)}
            okText="确认回滚"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="回滚">
              <Button size="small" danger icon={<RollbackOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  if (datasetsLoading) {
    return <div style={{ padding: 24, textAlign: 'center' }}><Spin /></div>;
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={4} style={{ margin: 0 }}>
          <HistoryOutlined style={{ marginRight: 8 }} />
          版本管理
        </Title>
        <Text type="secondary">管理本体定义的版本快照，支持版本对比与历史回滚</Text>
      </div>

      {datasets.length === 0 ? (
        <Alert
          type="info"
          message="暂无数据集"
          description="请先创建数据集后再使用版本管理功能。"
          style={{ marginBottom: 16 }}
        />
      ) : (
        <>
          <div style={{ marginBottom: 16 }}>
            <Space>
              <Text strong>数据集：</Text>
              <Select
                value={selectedDataset}
                onChange={(v) => {
                  setSelectedDataset(v);
                  setPage(1);
                }}
                style={{ width: 260 }}
                options={datasets.map((ds) => ({
                  value: ds.id,
                  label: ds.display_name || ds.id,
                }))}
              />
            </Space>
          </div>

          <Card>
            <Table
              columns={columns}
              dataSource={versions}
              rowKey="version_id"
              loading={loading}
              locale={{ emptyText: <Empty description="暂无版本记录 — 通过暂存区提交变更即可创建版本" /> }}
              pagination={{
                current: page,
                pageSize: 20,
                total,
                onChange: setPage,
                showTotal: (t) => `共 ${t} 个版本`,
              }}
            />
          </Card>
        </>
      )}

      {/* Version Detail Modal */}
      <Modal
        title={`版本详情 #${detailVersion?.version_number || ''}`}
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={800}
      >
        {detailLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
        ) : detailVersion ? (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="版本号">v{detailVersion.version_number}</Descriptions.Item>
            <Descriptions.Item label="版本 ID">{detailVersion.version_id}</Descriptions.Item>
            <Descriptions.Item label="提交信息" span={2}>{detailVersion.commit_message}</Descriptions.Item>
            <Descriptions.Item label="创建者">{detailVersion.created_by || '-'}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{detailVersion.created_at ? new Date(detailVersion.created_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
            <Descriptions.Item label="备注" span={2}>{detailVersion.notes || '无'}</Descriptions.Item>
            <Descriptions.Item label="变更摘要" span={2}>
              <Timeline
                items={(detailVersion.changes_summary || []).map((c, i) => ({
                  key: i,
                  color: c.change_type === 'create' ? 'green' : c.change_type === 'delete' ? 'red' : 'blue',
                  children: (
                    <span>
                      [{ENTITY_LABELS[c.entity_type] || c.entity_type}]
                      <Text strong> {c.entity_name}</Text>
                      <Tag color={
                        c.change_type === 'create' ? 'green' :
                        c.change_type === 'delete' ? 'red' : 'blue'
                      } style={{ marginLeft: 8 }}>
                        {c.change_type === 'create' ? '创建' : c.change_type === 'update' ? '更新' : '删除'}
                      </Tag>
                    </span>
                  ),
                }))}
              />
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Empty description="未找到版本信息" />
        )}
      </Modal>

      {/* Diff Modal */}
      <Modal
        title="版本对比"
        open={diffOpen}
        onCancel={() => setDiffOpen(false)}
        footer={null}
        width={900}
      >
        {diffLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
        ) : diffs.length === 0 ? (
          <Empty description="两个版本之间没有差异" />
        ) : (
          <List
            dataSource={diffs}
            renderItem={(item) => (
              <List.Item key={item.entity_type + item.entity_name + item.field}>
                <List.Item.Meta
                  title={
                    <Space>
                      <Tag>{ENTITY_LABELS[item.entity_type] || item.entity_type}</Tag>
                      <Text strong>{item.entity_name}</Text>
                      <Tag color="orange">{item.field}</Tag>
                    </Space>
                  }
                  description={
                    <div style={{ display: 'flex', gap: 16 }}>
                      <div style={{ flex: 1, background: '#fff1f0', padding: 8, borderRadius: 4 }}>
                        <Text type="danger" style={{ fontSize: 12 }}>旧值</Text>
                        <div style={{ wordBreak: 'break-all', fontSize: 13 }}>
                          {item.old_value === null ? <Text italic type="secondary">(无)</Text> :
                            typeof item.old_value === 'object' ? JSON.stringify(item.old_value, null, 2) :
                            String(item.old_value)}
                        </div>
                      </div>
                      <div style={{ flex: 1, background: '#f6ffed', padding: 8, borderRadius: 4 }}>
                        <Text type="success" style={{ fontSize: 12 }}>新值</Text>
                        <div style={{ wordBreak: 'break-all', fontSize: 13 }}>
                          {item.new_value === null ? <Text italic type="secondary">(无)</Text> :
                            typeof item.new_value === 'object' ? JSON.stringify(item.new_value, null, 2) :
                            String(item.new_value)}
                        </div>
                      </div>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Modal>

      {/* Edit Notes Modal */}
      <Modal
        title="编辑版本备注"
        open={notesOpen}
        onCancel={() => setNotesOpen(false)}
        onOk={handleEditNotes}
        confirmLoading={notesSaving}
        okText="保存"
        cancelText="取消"
      >
        <TextArea
          rows={4}
          value={notesText}
          onChange={(e) => setNotesText(e.target.value)}
          placeholder="添加备注信息..."
        />
      </Modal>
    </div>
  );
}
