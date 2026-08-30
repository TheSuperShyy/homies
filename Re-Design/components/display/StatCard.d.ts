/** Metric tile: label, value, signed delta. hero = large featured number. */
export interface StatCardProps {
  label: React.ReactNode;
  value: React.ReactNode;
  /** Signed change string, e.g. "+1.7%" or "-3.4%". */
  delta?: string;
  /** Muted trailing text next to the delta, e.g. "Units 104". */
  sub?: React.ReactNode;
  icon?: React.ReactNode;
  /** Large featured variant (Total Holding). */
  hero?: boolean;
  style?: React.CSSProperties;
}
export declare function StatCard(props: StatCardProps): JSX.Element;
