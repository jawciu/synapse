import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

function IconBase(props: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    />
  );
}

export function FlowerIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12 5c-1.8 0-3 1.2-3 3s1.2 3 3 3 3-1.2 3-3-1.2-3-3-3Z" />
      <path d="M12 3c1.6-2.3 5-1.5 5.4 1.3.2 1.3-.4 2.6-1.6 3.4" />
      <path d="M19.4 8.7c2.8-.4 4.6 2.6 2.9 5-.8 1.1-2.1 1.7-3.5 1.6" />
      <path d="M18.8 15.3c1.7 2.3-.1 5.4-3 5.1-1.3-.1-2.4-.9-2.9-2.1" />
      <path d="M11.3 18.3c-.7 2.7-4.2 3.4-6 .8-.9-.9-1.3-2.2-.9-3.4" />
      <path d="M6.2 14.9c-2.8.8-5.1-2-3.9-4.6.6-1.2 1.7-2 3.1-2.1" />
      <path d="M6.2 8.2C4 6.5 4.6 3 7.2 2.3c1.3-.3 2.7.1 3.6 1.1" />
    </IconBase>
  );
}

export function RefreshIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M21 12a9 9 0 0 0-15.4-6.4" />
      <path d="M3 4v4h4" />
      <path d="M3 12a9 9 0 0 0 15.4 6.4" />
      <path d="M21 20v-4h-4" />
    </IconBase>
  );
}

export function JournalIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M6 4h10a2 2 0 0 1 2 2v14H8a2 2 0 0 1-2-2V4Z" />
      <path d="M8 4v14" />
      <path d="M11.5 9h4.5" />
      <path d="M11.5 13h4.5" />
    </IconBase>
  );
}

export function PatternIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="6" cy="7" r="2.2" />
      <circle cx="18" cy="7" r="2.2" />
      <circle cx="12" cy="17" r="2.2" />
      <path d="M7.9 8.2 10.6 15" />
      <path d="M16.1 8.2 13.4 15" />
      <path d="M8.2 7h7.6" />
    </IconBase>
  );
}

export function EmotionIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12 20s-7-4.5-8.8-8.2C1.4 8.1 3.2 4.5 7 4.5c2.1 0 3.7 1 5 3 1.3-2 2.9-3 5-3 3.8 0 5.6 3.6 3.8 7.3C19 15.5 12 20 12 20Z" />
    </IconBase>
  );
}

export function ThemeIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="m12 3 1.6 3.9L17.5 8l-3 2.8.8 4.2-3.3-2-3.3 2 .8-4.2-3-2.8 3.9-1.1L12 3Z" />
      <path d="m18 14 .9 2.1L21 17l-2.1.8L18 20l-.9-2.2L15 17l2.1-.9L18 14Z" />
    </IconBase>
  );
}

export function PeopleIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="9" cy="8" r="2.5" />
      <circle cx="16.5" cy="9" r="2" />
      <path d="M4.5 18c.4-2.7 2.4-4.5 4.5-4.5h.1c2.1 0 4.1 1.8 4.5 4.5" />
      <path d="M14.2 18c.3-1.8 1.5-3.2 3.2-3.8" />
    </IconBase>
  );
}

export function BodySignalIcon(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M3 12h4l2-4 4 8 2-4h6" />
      <path d="M12 3v3" />
      <path d="M12 18v3" />
    </IconBase>
  );
}
