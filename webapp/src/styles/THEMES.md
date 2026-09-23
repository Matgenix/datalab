# Theme system architecture

This explains how `themes.css` and the rest of the theming code fit
together, and — the question that actually matters day to day — **when a
change needs a rebuild and when it doesn't.**

## The mental model

A theme is nothing but a named set of CSS custom properties (`--theme-*`),
switched on by one class on `<html>` (e.g. `theme-dark`). Every component
reads those tokens instead of hardcoded colors:

```css
color: var(--theme-body-color, #2c3e50);
```

The second argument is the fallback used when the active theme doesn't
define that token. This one mechanism is what makes almost everything else
in this doc possible.

There are two kinds of theme:

| | Built-in (Default, Dark, Forest, Sunset, Neon, Aurora, Pastel) | Custom (deployment-provided) |
|---|---|---|
| Defined in | `themes.css`, part of the app's source code | `public/custom/theme.css`, dropped in by whoever deploys the app |
| Ships in | the JS/CSS build | a static asset, untouched by the build |
| Editing it needs | a rebuild | nothing — see below |

## Architecture: where a color value comes from and where it goes

Three independent layers. A theme only ever touches layer 1.

```
1. DEFINITION                    2. ACTIVATION                    3. CONSUMPTION

.theme-dark {                 <html class="theme-dark">      Generic app CSS
  --theme-primary: #4dabf7        ^                          (.card, .btn-primary,
  --theme-body-bg: #14181c        |                           .form-control, labels...)
  ...                             |                                 ^
}                                 |                                 |
     ^                       store/index.js                   PrimeVue components
     |                       SET_THEME mutation                (DataTable, dropdowns)
     |                            ^                                 ^
     |                            |                            via the --p-* bridge
     |                  user picks in Settings                      |
     |                  (or FOUC script in                    A few components that
     |                  index.html applies a                  read --theme-* directly
     |                  default before Vue mounts)             (e.g. EditPage navbar)
     |
     +-- OR: deployment drops public/custom/theme.css instead of using themes.css
```

1. **Definition** — a flat set of `--theme-*` properties under one CSS
   class. Either built into `themes.css` (PART 1) or supplied by the
   deployment (`public/custom/theme.css`). This is the *only* layer that
   changes when a theme is added, edited, or removed.
2. **Activation** — exactly one theme class lives on `<html>` at a time.
   It gets there either because the user picked it in Settings (Vuex
   `SET_THEME` mutation, persisted to `localStorage`) or because
   `index.html`'s inline script applied a default *before Vue even
   mounted* (reading `localStorage`, falling back to the
   `VUE_APP_DEFAULT_THEME` build-time value, falling back to `default`) —
   that's purely to avoid a flash of the wrong theme; `App.vue` re-applies
   the same choice through the store immediately after, which is the real
   source of truth from then on.
3. **Consumption** — nothing here knows or cares which theme is active,
   or how many themes exist. Three kinds of consumer:
   - **Generic app CSS** — PART 3's "bridge" (`.card`, `.btn-primary`,
     `.form-control`, editor labels, alerts, badges...) reads `--theme-*`
     directly.
   - **PrimeVue components** (DataTable, filters, popovers) — these don't
     understand `--theme-*` at all; PrimeVue only reads its own `--p-*`
     namespace. PART 3 translates ours onto theirs once, for every theme
     at once (see `html[class^="theme-..."] { --p-content-background:
     var(--theme-card-bg); ... }`).
   - **A handful of individual components** that read a `--theme-*` token
     inline for something specific to them (e.g. `EditPage.vue` sets the
     navbar's background from `--theme-navbar-bg`).

### Why this doesn't get more expensive as it grows

Two decisions make both "add a theme" and "add a token" **O(1)** work,
regardless of how many themes or tokens already exist:

- **The bridge is written against "any non-default theme," never against a
  specific theme name.** PART 3 is gated on `html:not(.theme-default)` — it
  has no idea how many themes exist. Theme #8 costs exactly what theme #2
  cost: one palette block. PART 3/4 never grow when a theme is added.
- **Every consumer reads through `var(--x, fallback)`, never assumes a
  token exists.** A new token costs one line at its point of use and zero
  changes to any existing theme file — built-in or custom, seen or unseen —
  since they all inherit the fallback until they opt in.

That's the whole reason this scales flat instead of getting more painful
per theme/token over time — see the rebuild matrix and "adding a new
themeable thing" section below for the mechanics.

## File map

| File | Role |
|---|---|
| `webapp/src/styles/themes.css` | Everything above: palettes, the Bootstrap/PrimeVue "bridge", cosmetic extras. Read the big comment at the top of that file first — it documents the 4 parts. |
| `webapp/src/store/index.js` | The `THEMES` registry (name/label/swatch), `resolveTheme()`, `applyThemeClass()`, persistence to `localStorage`. |
| `webapp/src/primevue-theme-preset.js` | Tells PrimeVue which themes are dark (`darkModeSelector`) and defines shared DataTable/filter tweaks. |
| `webapp/public/index.html` | Inline script that applies the right theme class *before* Vue mounts (avoids a flash of the wrong theme), and injects the custom theme's `<link>`. |
| `webapp/src/App.vue` | `detectCustomTheme()` — reads the custom file's metadata at runtime and registers it with the store. |
| `webapp/public/custom/theme.css` | The deployment's custom theme. Gitignored — this is *config*, not app code. |
| `webapp/public/custom/theme.example.css` | Annotated template for the file above, with every token explained. |
| `pydatalab/docs/config.md` | User-facing docs: how a *deployment* adds a custom theme. This file is the developer-facing counterpart. |

## How the custom (drop-in) theme actually loads — step by step

1. `public/index.html`'s inline script injects
   `<link id="datalab-custom-theme-css" href=".../custom/theme.css" onerror="this.remove()">`.
   If the file is missing, the 404 removes the tag and nothing happens —
   this is what makes the file fully optional.
2. `App.vue`'s `detectCustomTheme()` reads a handful of *metadata* custom
   properties off `:root` via `getComputedStyle` — `--datalab-custom-theme`
   (a presence flag), `-label`, `-swatch`, `-scheme` — and calls
   `registerCustomTheme()`, which adds a "Custom" entry to the theme picker.
   It retries at 150/600/1500ms and again on the `<link>`'s `load` event,
   because the stylesheet can finish parsing after the component mounts.
3. Selecting "Custom" adds the class `theme-custom` (or `theme-custom-dark`
   if `--datalab-custom-theme-scheme: dark`) to `<html>`, which activates
   the actual palette in the file's `.theme-custom { }` block.

**None of this is aware of a build** — from the browser's point of view
`custom/theme.css` is a plain static file, the same as `favicon.ico`. But
whether editing it on disk shows up *without re-running the Docker build*
depends entirely on how it physically reaches that URL in your deployment:

| Deployment | Is `custom/theme.css` build-time or runtime? | Edit + reload picks it up? |
|---|---|---|
| Local dev (`yarn serve` / `vue-cli-service serve`) | Runtime — webpack-dev-server serves `public/` straight off disk. | **Yes**, always. |
| Production Docker image, **no volume mount** for it | Build-time — `.docker/app/Dockerfile` does `COPY webapp ./` then `vue-cli-service build`, which bakes whatever is in `public/custom/theme.css` *at build time* into `/app/dist/custom/theme.css` inside the image layer. The container's entrypoint only patches a few env-var placeholders in already-built files; it never re-reads or re-copies this file. | **No** — needs `docker compose build app` (or equivalent) to pick up an edit, same as any other source change. |
| Production Docker image, **with a volume mount** for it, e.g.: `- ./custom-theme.css:/app/dist/custom/theme.css:ro` | Runtime — the mount overrides the baked-in file inside the running container. | **Yes**, always — this is what makes the "just drop a file, no rebuild" promise actually true in production. |

Our current `docker-compose.yml` does **not** mount it — so today, in a
built/deployed image, editing the theme means rebuilding the image, exactly
like any other change. Add the volume above if you want true no-rebuild
editing in production.

## The rebuild matrix

| You changed... | Rebuild? | Why |
|---|---|---|
| A color in `public/custom/theme.css` | **No** in local dev. **Yes** in a built Docker image, *unless* it's volume-mounted (see table above). | Static file either way — whether a rebuild is needed depends on whether it's baked into the image or mounted from the host. |
| Added/removed a token in `public/custom/theme.css` | Same as above | The app only reads whichever tokens are present; see the fallback mechanism above — this part is true regardless of how the file reaches the browser. |
| A color in a *built-in* theme (`themes.css` PART 1) | **Yes** | Bundled into the compiled CSS. |
| Added a brand-new built-in theme | **Yes** | Touches `themes.css`, `store/index.js`, `index.html`, and usually `primevue-theme-preset.js` — all bundled. |
| Added a new `--theme-*` token for a new UI element | **Yes, once** — for the component using it. **No changes needed in any existing theme file**, built-in or custom (see below). |
| Removed/renamed a `--theme-*` token | **Yes**, for every call site using it (bundled code). Old custom `theme.css` files that still define the now-dead variable aren't broken — it's just an unused declaration, not an error. |
| `VUE_APP_DEFAULT_THEME` or any other `VUE_APP_*` env var | **Yes** | Webpack bakes these into the build; they aren't read at runtime. |

## Adding a new themeable thing (e.g. a color for a future 3D-molecule viewer)

1. At the point of use, reach for the token with a sensible fallback:
   ```css
   color: var(--theme-molecule-bond-color, #808080);
   ```
2. Done. Every existing theme — built-in and custom, including ones you've
   never seen — silently gets `#808080` until it opts in.
3. A theme that *wants* its own value just adds one line to itself. No
   registry, no migration step, nothing else to touch.

This is the whole reason every token in this system is read through
`var(--x, fallback)` rather than assumed to exist.

## Adding a new built-in theme

Per the header comment in `themes.css`:

1. One palette block in PART 1 (`.theme-yourname { --theme-primary: ...; }`).
2. One `--p-primary-*` ramp for PrimeVue, near the others in PART 3.
3. One line in `store/index.js`'s `THEMES` array (name/label/swatch).
4. Add the name to `VALID_THEMES` in `index.html` (or the FOUC snippet
   won't recognize a stored choice and will fall back to Default on reload).
5. **Only if the theme is dark-canvas**, also:
   - add it to the `html[class^="theme-..."]` selector list in PART 3 (the
     one that sets `--p-content-background` etc. explicitly), and
   - add it to `darkModeSelector` in `primevue-theme-preset.js`, and
   - add a `color-scheme: dark` rule for it, so native browser chrome
     (date-picker icon, scrollbars) renders light-on-dark.

   Do this even though PrimeVue *also* has its own light/dark switching:
   its own dark-mode CSS is generated as a `:root,:host` rule nested inside
   the theme's class selector, which under CSS nesting rules becomes a
   descendant combinator and can never match `<html class="theme-x">`
   itself — so it silently never applies. Don't rely on it; set the
   tokens explicitly, as PART 3 already does for every other dark theme.
6. PARTS 3/4 (Bootstrap/vue-select/editor support, contrast fixes) need
   **no changes** — they're gated on `html:not(.theme-default)` and apply
   to every theme automatically.

## Accessibility

Every `--theme-*` value in the built-in palettes was chosen to meet WCAG AA
(4.5:1 for body text, 3:1 for large text/UI). When adding or editing a
built-in theme, check new color pairs the same way — text color against
whatever background it actually sits on, not against `#fff` by default.
