/**
 * Pill filter tabs (1D 1W 1M · All Gainers Losers). Active = accent fill.
 * @startingPoint section="Navigation" subtitle="Pill tabs + sidebar nav" viewport="700x260"
 */
export interface TabsProps {
  items: string[];
  value: string;
  onChange?: (item: string) => void;
  size?: "sm" | "md";
  style?: React.CSSProperties;
}
export declare function Tabs(props: TabsProps): JSX.Element;
