/** Circular avatar; photo or initials fallback. */
export interface AvatarProps {
  src?: string;
  name?: string;
  /** Diameter px. Default 36. */
  size?: number;
  style?: React.CSSProperties;
}
export declare function Avatar(props: AvatarProps): JSX.Element;
