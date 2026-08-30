/** Pill text input (search bar style). */
export interface InputProps {
  /** Leading icon element (16px, currentColor). */
  icon?: React.ReactNode;
  size?: "sm" | "md" | "lg";
  placeholder?: string;
  value?: string;
  onChange?: (e: any) => void;
  style?: React.CSSProperties;
}
export declare function Input(props: InputProps): JSX.Element;
