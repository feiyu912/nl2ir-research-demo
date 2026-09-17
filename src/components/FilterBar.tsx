import type { ReactNode } from 'react';

type Props = {
  children: ReactNode;
};

export default function FilterBar({ children }: Props) {
  return <div className="filter-bar">{children}</div>;
}
