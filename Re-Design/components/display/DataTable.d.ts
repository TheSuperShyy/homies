/** Hairline-divided data table (Portfolio Overview, Watchlist). */
export interface DataTableColumn {
  key: string;
  label: React.ReactNode;
  align?: "left" | "right" | "center";
  /** Custom cell renderer. */
  render?: (row: any) => React.ReactNode;
}
export interface DataTableProps {
  columns: DataTableColumn[];
  rows: any[];
  style?: React.CSSProperties;
}
export declare function DataTable(props: DataTableProps): JSX.Element;
