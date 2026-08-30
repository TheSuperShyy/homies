/** Small pill label. Also exports Delta — signed colored change value. */
export interface BadgeProps {
  tone?: "neutral" | "positive" | "negative" | "accent";
  children: React.ReactNode;
  style?: React.CSSProperties;
}
export declare function Badge(props: BadgeProps): JSX.Element;

export interface DeltaProps {
  /** e.g. "+3.68 ($ 5.32)" or "-3.4%". Leading "-" renders negative/red. */
  value: string;
  showArrow?: boolean;
  style?: React.CSSProperties;
}
export declare function Delta(props: DeltaProps): JSX.Element;
