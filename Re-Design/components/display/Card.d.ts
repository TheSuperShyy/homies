/**
 * Surface container: bordered card on dark, soft-shadow card on light.
 * @startingPoint section="Display" subtitle="Cards, stat tiles, data table" viewport="700x360"
 */
export interface CardProps {
  /** Card title row (14px semibold) with optional right-side action. */
  title?: React.ReactNode;
  action?: React.ReactNode;
  /** Nested tile styling (surface-2, tighter radius) for tiles inside cards. */
  nested?: boolean;
  padding?: number | string;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}
export declare function Card(props: CardProps): JSX.Element;
