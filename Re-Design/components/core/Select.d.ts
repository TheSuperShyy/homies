/** Pill dropdown select with chevron. */
export interface SelectProps {
  options: string[];
  value?: string;
  onChange?: (e: any) => void;
  size?: "sm" | "md" | "lg";
  style?: React.CSSProperties;
}
export declare function Select(props: SelectProps): JSX.Element;
