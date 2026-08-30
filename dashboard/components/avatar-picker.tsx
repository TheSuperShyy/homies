'use client';

import { useRef, useState, useTransition } from 'react';

/**
 * The profile photo control — and the second client component in this app.
 *
 * WHY IT IS ONE, when the rest of the dashboard is forms posting to server
 * actions with no JavaScript at all. Because the resizing has to happen in the
 * browser. There is no image library on the server and adding one for this
 * would be a native dependency in the build; without resizing, what gets stored
 * is whatever came off somebody's phone, and that file is then fetched behind
 * the topbar of every page they open. A canvas turns a 4MB photograph into
 * about 20KB before it leaves the machine, and it costs a hundred lines.
 *
 * The upload itself still happens on the server, in `saveAvatar`. The browser's
 * only job is to shrink the image and hand it over.
 *
 * Labels arrive as props for the same reason the login form's do: the language
 * is a cookie, `cookies()` is server-only, and a client component that guessed
 * from `navigator.language` would disagree with every page around it.
 */

export type AvatarLabels = {
  choose: string; change: string; remove: string; save: string; saving: string;
  hint: string; errType: string; errBig: string; errRead: string;
};

/** Bigger than any phone photo; the point is to reject a video, not to be strict. */
const MAX_SOURCE = 20 * 1024 * 1024;
const SIDE = 256;

/**
 * Centre-cropped to a square and drawn at 256px.
 *
 * Centre-cropped rather than squashed: every place this image appears is a
 * circle, so a portrait photograph letterboxed into a square would show as a
 * face with two grey bands, and a stretched one would show as a face that is
 * the wrong shape.
 */
async function squareImage(file: File): Promise<string> {
  const bitmap = await createImageBitmap(file);
  const side = Math.min(bitmap.width, bitmap.height);
  const canvas = document.createElement('canvas');
  canvas.width = SIDE;
  canvas.height = SIDE;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('no 2d context');
  ctx.drawImage(
    bitmap,
    (bitmap.width - side) / 2, (bitmap.height - side) / 2, side, side,
    0, 0, SIDE, SIDE,
  );
  bitmap.close?.();
  // WebP where it encodes, JPEG where it does not. `toDataURL` does not throw
  // on a format it cannot produce — it silently returns a PNG, which at 256px
  // is four times the size — so the prefix has to be checked rather than
  // assumed.
  const webp = canvas.toDataURL('image/webp', 0.86);
  return webp.startsWith('data:image/webp') ? webp : canvas.toDataURL('image/jpeg', 0.86);
}

export function AvatarPicker({ current, initials, labels, save, remove }: {
  current: string;
  initials: string;
  labels: AvatarLabels;
  save: (formData: FormData) => Promise<void>;
  remove: () => Promise<void>;
}) {
  const [data, setData] = useState('');
  const [preview, setPreview] = useState('');
  const [err, setErr] = useState('');
  const [pending, start] = useTransition();
  const file = useRef<HTMLInputElement>(null);

  async function pick(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    // Reset immediately, so choosing the same file twice after an error still
    // fires a change event.
    e.target.value = '';
    if (!f) return;
    if (!f.type.startsWith('image/')) { setErr(labels.errType); return; }
    if (f.size > MAX_SOURCE) { setErr(labels.errBig); return; }
    setErr('');
    try {
      const url = await squareImage(f);
      setData(url);
      setPreview(url);
    } catch {
      // A file the browser cannot decode: a HEIC on a browser without support,
      // a renamed .txt, a corrupt download. Nothing here can fix it, so say so.
      setErr(labels.errRead);
    }
  }

  const shown = preview || current;

  return (
    <div className="avatarpick">
      <span className="avatar xl" aria-hidden="true">
        {shown ? <img src={shown} alt="" /> : initials}
      </span>

      <div className="avatarpick-side">
        <input ref={file} type="file" accept="image/*" onChange={pick} hidden />

        <div className="choice">
          <button type="button" onClick={() => file.current?.click()}>
            {current ? labels.change : labels.choose}
          </button>

          {data && (
            <button type="button" className="go" disabled={pending}
                    onClick={() => start(async () => {
                      const fd = new FormData();
                      fd.set('image', data);
                      await save(fd);
                    })}>
              {pending ? labels.saving : labels.save}
            </button>
          )}

          {current && !data && (
            <button type="button" className="danger" disabled={pending}
                    onClick={() => start(() => remove())}>
              {labels.remove}
            </button>
          )}
        </div>

        {/* One line that is either the hint or the reason the last attempt did
            not work. `role="alert"` only when it is the latter — a live region
            that announces the standing hint on every render is noise. */}
        <p className={err ? 'hint bad' : 'hint'} role={err ? 'alert' : undefined}>
          {err || labels.hint}
        </p>
      </div>
    </div>
  );
}
