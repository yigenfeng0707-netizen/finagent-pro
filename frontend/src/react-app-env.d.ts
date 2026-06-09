declare module 'antd' {
  import React from 'react';

  // Layout
  export const Layout: React.FC<any> & { Sider: React.FC<any>; Content: React.FC<any>; Header: React.FC<any>; Footer: React.FC<any> };
  export const Menu: React.FC<any> & { Item: React.FC<any> };
  export const Card: React.FC<any>;
  export const Row: React.FC<any>;
  export const Col: React.FC<any>;
  export const Statistic: React.FC<any>;
  export const Button: React.FC<any>;
  export const Input: React.FC<any> & { TextArea: React.FC<any>; Search: React.FC<any> };
  export const Select: React.FC<any> & { Option: React.FC<any> };
  export const Tabs: React.FC<any> & { TabPane: React.FC<any> };
  export const List: React.FC<any> & { Item: React.FC<any> & { Meta: React.FC<any> } };
  export const Tag: React.FC<any>;
  export const Spin: React.FC<any>;
  export const message: { info: (msg: string) => void; success: (msg: string) => void; error: (msg: string) => void; warning: (msg: string) => void; loading: (msg: string) => void; destroy: () => void };
  export const ConfigProvider: React.FC<any>;
  export const Space: React.FC<any>;
  export const Typography: { Title: React.FC<any>; Text: React.FC<any>; Paragraph: React.FC<any> };
  export const Table: React.FC<any>;
  export const Divider: React.FC<any>;
  export const Modal: React.FC<any>;
  export const Tooltip: React.FC<any>;
  export const Empty: React.FC<any> & { PRESENTED_IMAGE_SIMPLE: string; PRESENTED_IMAGE_DEFAULT: string };
  export const Alert: React.FC<any>;
  export const Breadcrumb: React.FC<any> & { Item: React.FC<any> };
  export const Avatar: React.FC<any>;
  export const Checkbox: React.FC<any>;
  export const Collapse: React.FC<any> & { Panel: React.FC<any> };
  export const Progress: React.FC<any>;
  export const Switch: React.FC<any>;
  export const Timeline: React.FC<any> & { Item: React.FC<any> };
  export const Radio: React.FC<any> & { Group: React.FC<any>; Button: React.FC<any> };
  export const Form: React.FC<any> & { Item: React.FC<any>; List: React.FC<any> };
  export const DatePicker: React.FC<any>;
  export const Dropdown: React.FC<any>;
  export const Badge: React.FC<any>;
  export const Popover: React.FC<any>;
  export const Popconfirm: React.FC<any>;
  export const Drawer: React.FC<any>;
  export const Skeleton: React.FC<any>;
  export const Result: React.FC<any>;
  export const Descriptions: React.FC<any> & { Item: React.FC<any> };
  export const Steps: React.FC<any> & { Step: React.FC<any> };
  export const Upload: React.FC<any>;
  export const notification: { info: (config: any) => void; success: (config: any) => void; error: (config: any) => void; warning: (config: any) => void; open: (config: any) => void; close: (key: string) => void; destroy: () => void };
}

declare module '@ant-design/icons' {
  import React from 'react';

  export const DashboardOutlined: React.FC<any>;
  export const LineChartOutlined: React.FC<any>;
  export const PieChartOutlined: React.FC<any>;
  export const SafetyOutlined: React.FC<any>;
  export const RobotOutlined: React.FC<any>;
  export const SettingOutlined: React.FC<any>;
  export const ThunderboltOutlined: React.FC<any>;
  export const RiseOutlined: React.FC<any>;
  export const MenuFoldOutlined: React.FC<any>;
  export const MenuUnfoldOutlined: React.FC<any>;
  export const BellOutlined: React.FC<any>;
  export const UserOutlined: React.FC<any>;
  export const ReloadOutlined: React.FC<any>;
  export const SendOutlined: React.FC<any>;
  export const CheckCircleOutlined: React.FC<any>;
  export const CloseCircleOutlined: React.FC<any>;
  export const LoadingOutlined: React.FC<any>;
  export const SyncOutlined: React.FC<any>;
  export const ArrowLeftOutlined: React.FC<any>;
  export const ArrowRightOutlined: React.FC<any>;
  export const DownOutlined: React.FC<any>;
  export const UpOutlined: React.FC<any>;
  export const InfoCircleOutlined: React.FC<any>;
  export const ExclamationCircleOutlined: React.FC<any>;
  export const FileTextOutlined: React.FC<any>;
  export const EyeOutlined: React.FC<any>;
  export const DownloadOutlined: React.FC<any>;
  export const CopyOutlined: React.FC<any>;
  export const DeleteOutlined: React.FC<any>;
  export const EditOutlined: React.FC<any>;
  export const SearchOutlined: React.FC<any>;
  export const CloseOutlined: React.FC<any>;
  export const CheckOutlined: React.FC<any>;
  export const PlusOutlined: React.FC<any>;
  export const MinusOutlined: React.FC<any>;
  export const PlayCircleOutlined: React.FC<any>;
  export const PauseCircleOutlined: React.FC<any>;
  export const ApiOutlined: React.FC<any>;
  export const TeamOutlined: React.FC<any>;
  export const BulbOutlined: React.FC<any>;
  export const FundOutlined: React.FC<any>;
  export const FallOutlined: React.FC<any>;
  export const ClockCircleOutlined: React.FC<any>;
  export const ToolOutlined: React.FC<any>;
  export const SwapOutlined: React.FC<any>;
  export const StockOutlined: React.FC<any>;
  export const BarChartOutlined: React.FC<any>;
  export const AreaChartOutlined: React.FC<any>;
  export const DotChartOutlined: React.FC<any>;
  export const TransactionOutlined: React.FC<any>;
  export const DollarOutlined: React.FC<any>;
  export const WalletOutlined: React.FC<any>;
  export const CloudSyncOutlined: React.FC<any>;
  export const LinkOutlined: React.FC<any>;
  export const BranchesOutlined: React.FC<any>;
  export const NodeIndexOutlined: React.FC<any>;
  export const DeploymentUnitOutlined: React.FC<any>;
}

declare module 'echarts-for-react' {
  import React from 'react';
  const ReactECharts: React.FC<{
    option: any;
    style?: React.CSSProperties;
    className?: string;
    theme?: string;
    onChartReady?: (chart: any) => void;
    showLoading?: boolean;
    loadingOption?: any;
    notMerge?: boolean;
    lazyUpdate?: boolean;
    opts?: any;
    [key: string]: any;
  }>;
  export default ReactECharts;
}
