/** Circular icon-only button (topbar bell, settings, card expand chevron). */
export interface IconButtonProps {
  variant?: "solid" | "outline" | "ghost";
  /** Diameter in px. Default 38. */
  size?: number;
  /** Accessible label (required — icon-only). */
  label: string;
  /** The icon element, 16–18px, currentColor. */
  children: React.ReactNode;
  onClick?: () => void;
  style?: React.CSSProperties;
}
export declare function IconButton(props: IconButtonProps): JSX.Element;
