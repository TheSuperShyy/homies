/**
 * Pill-shaped action button.
 * @startingPoint section="Core" subtitle="Pill buttons — primary, secondary, ghost" viewport="700x220"
 */
export interface ButtonProps {
  /** Visual style. primary = accent fill; secondary = bordered pill; ghost = text-only. */
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
  /** Optional leading icon element (16px, currentColor). */
  icon?: React.ReactNode;
  disabled?: boolean;
  children?: React.ReactNode;
  onClick?: () => void;
  style?: React.CSSProperties;
}
export declare function Button(props: ButtonProps): JSX.Element;
