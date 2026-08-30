/** Sidebar nav row; active = solid accent fill. Also exports SidebarSection — uppercase group label. */
export interface SidebarItemProps {
  icon?: React.ReactNode;
  label: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
  style?: React.CSSProperties;
}
export declare function SidebarItem(props: SidebarItemProps): JSX.Element;

export interface SidebarSectionProps {
  label: React.ReactNode;
  style?: React.CSSProperties;
}
export declare function SidebarSection(props: SidebarSectionProps): JSX.Element;
