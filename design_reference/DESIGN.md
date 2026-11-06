---
name: MindVault Verification Engine
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#434655'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#747686'
  outline-variant: '#c4c5d7'
  surface-tint: '#2151da'
  primary: '#0037b0'
  on-primary: '#ffffff'
  primary-container: '#1d4ed8'
  on-primary-container: '#cad3ff'
  inverse-primary: '#b7c4ff'
  secondary: '#515f74'
  on-secondary: '#ffffff'
  secondary-container: '#d5e3fc'
  on-secondary-container: '#57657a'
  tertiary: '#004f35'
  on-tertiary: '#ffffff'
  tertiary-container: '#006948'
  on-tertiary-container: '#76eab6'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dce1ff'
  primary-fixed-dim: '#b7c4ff'
  on-primary-fixed: '#001551'
  on-primary-fixed-variant: '#0039b5'
  secondary-fixed: '#d5e3fc'
  secondary-fixed-dim: '#b9c7df'
  on-secondary-fixed: '#0d1c2e'
  on-secondary-fixed-variant: '#3a485b'
  tertiary-fixed: '#85f8c4'
  tertiary-fixed-dim: '#68dba9'
  on-tertiary-fixed: '#002114'
  on-tertiary-fixed-variant: '#005137'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 30px
    fontWeight: '600'
    lineHeight: 38px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 22px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.02em
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-desktop: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

This design system targets enterprise legal teams, brand directors, and compliance officers who audit marketing assets against regulatory standards and internal brand truths. The aesthetic rejects decorative AI gimmicks—avoiding vibrant gradients, purple glows, and frosted glass—in favor of engineered precision, clarity, and structural restraint inspired by high-density toolsets like Linear.

Key principles:
- **Calm Authority:** High-legibility utility over decorative expression. The workspace recedes so that analyzed text, citations, and compliance deltas stand forward.
- **Structural Density:** Compact, information-dense modules that prioritize scan speed, tabular alignment, and explicit state signals.
- **Architectural Framing:** Contrast is achieved through precise hairline dividers and muted tonal planar shifts rather than heavy drop shadows.

## Colors

The system uses a calibrated neutral-slate scale with selective, high-semantic signaling tokens:

- **Surfaces & Canvases:**
  - Canvas Base: `#F8F9FA`
  - Canvas Inset / Sidebar: `#F1F5F9`
  - Card & Active Workspace Surface: `#FFFFFF`
  - Subdued Panel: `#F8FAFC`
- **Borders & Dividers:**
  - Hairline Rule / Default Border: `#E2E8F0`
  - Active / Focus Border: `#CBD5E1`
  - Selected / Key Focus Border: `#1D4ED8`
- **Typography & Icons:**
  - Primary Content: `#0F172A`
  - Secondary Content: `#475569`
  - Tertiary / Micro Muted: `#94A3B8`
- **Semantic Accents:**
  - Action / Focus (Primary): `#1D4ED8` (Hover: `#1E40AF`, Subtle Bg: `#EFF6FF`)
  - Compliant (Success): `#059669` (Subtle Bg: `#ECFDF5`, Border: `#A7F3D0`)
  - Warning / Advisory: `#D97706` (Subtle Bg: `#FEF3C7`, Border: `#FDE68A`)
  - Violation / Discrepancy (Destructive): `#DC2626` (Subtle Bg: `#FEE2E2`, Border: `#FECACA`)

## Typography

Typography prioritizes information density and cross-reference readability:
- **Primary Interface:** Inter is deployed across all standard headers, descriptions, and structural controls. Activate `tnum` (tabular numbers) across data tables, audit scores, timestamp logs, and metrics.
- **Technical & Citations:** JetBrains Mono is assigned to legal clauses, citation IDs, strict rule matches, and hash fingerprints to separate contextual system metadata from narrative marketing copy.
- **Hierarchy Rules:** Keep headers disciplined and compact—page titles do not exceed 30px. Use medium font weights (`500`) for functional metadata to preserve distinction without visual clutter.

## Layout & Spacing

The layout is built for density and multi-pane analytical workflows:
- **Grid Architecture:** Multi-column workspace layouts (e.g., source copy, real-time audit findings, rule inspector) adhere to a 12-column dynamic grid or fixed-width functional rails (collapsible sidebars at 240px; inspector sidebars at 360px).
- **Rhythm:** Spacing follows an 8px base rhythm with 4px sub-increments (`0.25rem` / 4px and `0.5rem` / 8px). Avoid arbitrary white space gaps; data lists, inspector attributes, and verification logs must sit adjacent without superfluous padding.
- **Breakpoints:**
  - Desktop (>1280px): 3-panel split view active (Navigation, Verification Document, Findings Rail).
  - Tablet (768px - 1279px): Inspector rail collapses into an overlay or bottom sheet; document stays centered.
  - Mobile (<768px): Single-column stack with segmented mode switches between asset view and compliance flags.

## Elevation & Depth

Visual hierarchy relies on planar separation and crisp hairline boundaries rather than dramatic shadows:

- **Planes & Outlines:** Every container, editor surface, and card uses a 1px solid border (`#E2E8F0`).
- **Minimal Shadow Scale:**
  - Level 0 (Base / Cards): No shadow (`box-shadow: none`), framed entirely by `#E2E8F0` borders against `#F8F9FA` canvas.
  - Level 1 (Hover / Subdued Elevation): `0 1px 2px 0 rgba(15, 23, 42, 0.04)`.
  - Level 2 (Dropdowns / Flyout Menus / Popovers): `0 4px 6px -1px rgba(15, 23, 42, 0.07), 0 2px 4px -2px rgba(15, 23, 42, 0.05)`, encased in a `#E2E8F0` border.
  - Level 3 (Modal / Verification Dialogues): `0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.03)` with a neutral backdrop scrim (`#0F172A` at 20% opacity).

## Shapes

The interface uses restrained, compact border radii:
- Controls (Buttons, Inputs, Selectors): `4px` (`rounded` or `0.25rem`) for an engineered, desktop-first feel.
- Cards, Modals, Panels: `6px` (`rounded-lg` or `0.375rem`), maintaining strict geometric alignment across dense interfaces.
- Inline Status Chips & Badges: `4px` with tight padding; avoid circular or pill badges except for count tags.

## Components

- **Buttons:**
  - *Primary:* Solid `#1D4ED8` background, `#FFFFFF` text, `4px` border radius, 0 1px 2px shadow. Active state shifts to `#1E40AF`.
  - *Secondary:* `#FFFFFF` background, 1px solid `#E2E8F0` border, `#0F172A` text. Hover: `#F8FAFC` surface with `#CBD5E1` border.
  - *Destructive:* `#DC2626` text, `#FEE2E2` background, 1px solid `#FECACA` border.
  - *Height & Sizing:* Compact by default (32px standard control height, 28px dense table row height).

- **Compliance Status Badges & Chips:**
  - Micro tags built with `label-sm` font styles.
  - *Format:* 1px solid border matching semantic intent with a light tint background (e.g., Error: text `#DC2626`, background `#FEE2E2`, border `#FECACA`). No soft glow or oversized pills.

- **Form Inputs & Search Controls:**
  - Height: 32px standard.
  - Background: `#FFFFFF`. Border: 1px solid `#E2E8F0`.
  - Focus State: Unbroken ring with 1px border `#1D4ED8` and crisp focus ring (`box-shadow: 0 0 0 1px #1D4ED8`). No ambient blur.

- **Checkboxes & Selection Controls:**
  - 14px x 14px with `2px` border radius. 1px solid border `#CBD5E1`.
  - Checked state: `#1D4ED8` background with centered crisp white check icon.

- **Audit Cards & Issue Lists:**
  - White `#FFFFFF` surface bordered by 1px solid `#E2E8F0`.
  - Internal divider lines at 1px `#F1F5F9`.
  - Hover state shifts border to `#CBD5E1` without shifting position or invoking heavy drop shadows.

- **Citations & Regulatory Rules Block:**
  - Embedded container with `#F8FAFC` background and 1px solid `#E2E8F0` hairline border.
  - Rule IDs formatted in `code-sm` (`JetBrains Mono`).
  - Text highlights for discrepancies use precise `#FEE2E2` underlines or spans without degrading body legibility.