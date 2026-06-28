"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

interface Suggestion {
  display_name: string;
  lat: number;
  lon: number;
  city: string | null;
}

export default function SearchBox({ defaultAddress }: { defaultAddress: string }) {
  const router = useRouter();
  const [value, setValue] = useState(defaultAddress);
  const [items, setItems] = useState<Suggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [loading, setLoading] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const seq = useRef(0);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function onChange(next: string) {
    setValue(next);
    setActive(-1);
    if (debounce.current) clearTimeout(debounce.current);
    if (next.trim().length < 3) {
      setItems([]);
      setOpen(false);
      return;
    }
    debounce.current = setTimeout(async () => {
      const mySeq = ++seq.current;
      setLoading(true);
      try {
        const resp = await fetch(`/api/suggest?q=${encodeURIComponent(next)}`);
        const data: Suggestion[] = await resp.json();
        if (mySeq === seq.current) {
          setItems(data);
          setOpen(data.length > 0);
        }
      } catch {
        if (mySeq === seq.current) setItems([]);
      } finally {
        if (mySeq === seq.current) setLoading(false);
      }
    }, 250);
  }

  function go(address: string) {
    const a = address.trim();
    if (!a) return;
    setOpen(false);
    router.push(`/?address=${encodeURIComponent(a)}`);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open || items.length === 0) {
      if (e.key === "Enter") go(value);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => Math.min(i + 1, items.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, -1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      go(active >= 0 ? items[active].display_name : value);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={boxRef} className="searchbox">
      <div className="search">
        <input
          type="text"
          value={value}
          placeholder="Например: Москва, Тверская 7"
          autoComplete="off"
          autoFocus
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          onFocus={() => items.length > 0 && setOpen(true)}
          aria-expanded={open}
          aria-autocomplete="list"
        />
        <button className="btn" type="button" onClick={() => go(value)}>
          {loading ? "…" : "Посчитать"}
        </button>
      </div>

      {open && items.length > 0 && (
        <ul className="suggest" role="listbox">
          {items.map((s, i) => (
            <li
              key={`${s.lat},${s.lon},${i}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? "active" : ""}
              onMouseEnter={() => setActive(i)}
              onMouseDown={(e) => {
                e.preventDefault();
                go(s.display_name);
              }}
            >
              <span className="pin">📍</span>
              <span className="text">{s.display_name}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
