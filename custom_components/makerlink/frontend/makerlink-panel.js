// MakerLink sidebar panel: overview of all configured readers (machines & doors).
// Plain web component, no build step. Data comes live via the websocket
// command "makerlink/subscribe" (see ws_api.py), actions via "makerlink/action".

const TEXT = {
  de: {
    title: "MakerLink",
    loading: "Lade Reader…",
    notConfigured: "MakerLink ist noch nicht eingerichtet. Einstellungen → Geräte & Dienste → Integration hinzufügen → MakerLink.",
    noUnits: "Noch keine Maschinen oder Türen angelegt. In der MakerLink-Integration „Maschine oder Tür hinzufügen“ wählen.",
    error: "Fehler beim Laden",
    machine: "Maschine",
    door: "Tür",
    user: "Benutzer",
    runtime: "Laufzeit",
    cooldown: "Nachlauf",
    lastCost: "Letzte Kosten",
    balance: "Guthaben",
    power: "Schaltziel",
    interlock: "Sicherheitsschalter",
    reader: "Reader",
    pending: "Offene Buchungen",
    type: "Abrechnung",
    on: "an",
    off: "aus",
    unavailable: "nicht erreichbar",
    online: "online",
    offline: "offline",
    closed: "zu",
    open: "offen",
    stopSession: "Session beenden",
    endCooldown: "Nachlauf beenden",
    confirmStop: "Session von {user} an {name} beenden und abrechnen?",
    outOfOrder: "Außer Betrieb",
    admin: "Admin-Modus",
    openDoor: "Tür öffnen",
    device: "Gerät",
    lastAccess: "Letzter Zutritt",
    granted: "erlaubt",
    denied: "abgelehnt",
    summaryActive: "aktiv",
    summaryOoo: "außer Betrieb",
    summaryOffline: "offline",
    summaryPending: "offene Buchungen",
    status: {
      idle: "Bereit",
      checking: "Prüfe",
      active: "Aktiv",
      stopping: "Stoppt",
      cooldown: "Nachlauf",
      admin: "Admin-Modus",
      out_of_order: "Außer Betrieb",
      message: "Meldung",
      interlock_open: "Tür offen",
    },
    types: { machine: "kostenlos", laser: "Laser", "3dprint": "3D-Druck", dtf: "DTF", kiln: "Brennofen" },
  },
  en: {
    title: "MakerLink",
    loading: "Loading readers…",
    notConfigured: "MakerLink is not set up yet. Settings → Devices & services → Add integration → MakerLink.",
    noUnits: "No machines or doors yet. Use “Add machine or door” in the MakerLink integration.",
    error: "Error while loading",
    machine: "Machine",
    door: "Door",
    user: "User",
    runtime: "Runtime",
    cooldown: "Cooldown",
    lastCost: "Last cost",
    balance: "Balance",
    power: "Switch target",
    interlock: "Interlock",
    reader: "Reader",
    pending: "Pending bookings",
    type: "Billing",
    on: "on",
    off: "off",
    unavailable: "unavailable",
    online: "online",
    offline: "offline",
    closed: "closed",
    open: "open",
    stopSession: "Stop session",
    endCooldown: "End cooldown",
    confirmStop: "Stop and bill the session of {user} on {name}?",
    outOfOrder: "Out of order",
    admin: "Admin mode",
    openDoor: "Open door",
    device: "Device",
    lastAccess: "Last access",
    granted: "granted",
    denied: "denied",
    summaryActive: "active",
    summaryOoo: "out of order",
    summaryOffline: "offline",
    summaryPending: "pending bookings",
    status: {
      idle: "Idle",
      checking: "Checking",
      active: "Active",
      stopping: "Stopping",
      cooldown: "Cooldown",
      admin: "Admin mode",
      out_of_order: "Out of order",
      message: "Message",
      interlock_open: "Door open",
    },
    types: { machine: "free", laser: "Laser", "3dprint": "3D print", dtf: "DTF", kiln: "Kiln" },
  },
};

const STATUS_COLOR = {
  idle: "var(--success-color, #43a047)",
  checking: "var(--info-color, #039be5)",
  active: "var(--primary-color, #03a9f4)",
  stopping: "var(--info-color, #039be5)",
  cooldown: "var(--warning-color, #ffa600)",
  admin: "var(--accent-color, #ff9800)",
  out_of_order: "var(--error-color, #db4437)",
  message: "var(--info-color, #039be5)",
  interlock_open: "var(--warning-color, #ffa600)",
};

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const formatDuration = (seconds) => {
  seconds = Math.max(0, Math.floor(seconds));
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const mm = String(m).padStart(2, "0");
  const ss = String(s).padStart(2, "0");
  return h > 0 ? `${h}:${mm}:${ss}` : `${m}:${ss}`;
};

class MakerLinkPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._units = [];
    this._configured = true;
    this._loaded = false;
    this._error = null;
    this._unsub = null;
    this._busy = new Set();
  }

  // ----- properties set by Home Assistant -------------------------------------

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      this._renderShell();
      this._subscribe();
    }
    this._updateMenuButton();
  }

  set narrow(narrow) {
    this._narrow = narrow;
    this._updateMenuButton();
  }

  set panel(panel) {
    this._panel = panel;
  }

  connectedCallback() {
    this._timer = setInterval(() => this._tickDurations(), 1000);
    if (this._hass) {
      this._renderShell();
      this._subscribe();
    }
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    if (this._unsub) {
      this._unsub.then((unsub) => unsub()).catch(() => {});
      this._unsub = null;
    }
  }

  // ----- data -------------------------------------------------------------------

  get _t() {
    const lang = (this._hass?.language || "en").slice(0, 2);
    return TEXT[lang] || TEXT.en;
  }

  _subscribe() {
    if (this._unsub || !this._hass || !this.isConnected) return;
    this._unsub = this._hass.connection.subscribeMessage(
      (msg) => {
        this._units = msg.units || [];
        this._configured = msg.configured !== false;
        this._loaded = true;
        this._error = null;
        this._render();
      },
      { type: "makerlink/subscribe" }
    );
    this._unsub.catch((err) => {
      this._error = err?.message || String(err);
      this._unsub = null;
      this._render();
    });
  }

  async _action(unitId, action, value) {
    const key = `${unitId}:${action}`;
    if (this._busy.has(key)) return;
    this._busy.add(key);
    this._render();
    try {
      const msg = { type: "makerlink/action", unit: unitId, action };
      if (value !== undefined) msg.value = value;
      await this._hass.callWS(msg);
    } catch (err) {
      this._error = err?.message || String(err);
    } finally {
      this._busy.delete(key);
      this._render();
    }
  }

  // ----- rendering --------------------------------------------------------------

  _renderShell() {
    if (this._shellRendered) return;
    this._shellRendered = true;
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <div class="toolbar">
        <ha-menu-button></ha-menu-button>
        <div class="main-title">${esc(this._t.title)}</div>
      </div>
      <div class="content"></div>`;
    this.shadowRoot.querySelector(".content").addEventListener("click", (ev) => this._onClick(ev));
    this._updateMenuButton();
  }

  _updateMenuButton() {
    const button = this.shadowRoot?.querySelector("ha-menu-button");
    if (button && this._hass) {
      button.hass = this._hass;
      button.narrow = this._narrow;
    }
  }

  _render() {
    const content = this.shadowRoot.querySelector(".content");
    if (!content) return;
    const t = this._t;
    let html = "";
    if (this._error) html += `<div class="banner error">${esc(t.error)}: ${esc(this._error)}</div>`;
    if (!this._loaded) {
      html += `<div class="empty">${esc(t.loading)}</div>`;
    } else if (!this._configured) {
      html += `<div class="empty">${esc(t.notConfigured)}</div>`;
    } else if (!this._units.length) {
      html += `<div class="empty">${esc(t.noUnits)}</div>`;
    } else {
      html += this._renderSummary();
      html += `<div class="grid">${this._units.map((u) => this._renderUnit(u)).join("")}</div>`;
    }
    content.innerHTML = html;
    this._tickDurations();
  }

  _renderSummary() {
    const t = this._t;
    const count = (fn) => this._units.filter(fn).length;
    const chips = [
      [count((u) => u.session_active), t.summaryActive, STATUS_COLOR.active],
      [count((u) => u.out_of_order), t.summaryOoo, STATUS_COLOR.out_of_order],
      [count((u) => u.reader_online === false), t.summaryOffline, "var(--error-color, #db4437)"],
      [this._units.reduce((n, u) => n + (u.pending_bookings || 0), 0), t.summaryPending, STATUS_COLOR.cooldown],
    ];
    return `<div class="summary">${chips
      .map(([n, label, color]) => `<span class="chip ${n ? "" : "muted"}" style="--chip:${color}"><b>${n}</b> ${esc(label)}</span>`)
      .join("")}</div>`;
  }

  _renderUnit(u) {
    const t = this._t;
    const isMachine = u.kind === "machine";
    const statusLabel = t.status[u.status] || u.status;
    const color = u.reader_online === false ? "var(--disabled-text-color, #9e9e9e)" : STATUS_COLOR[u.status] || "var(--secondary-text-color)";
    const rows = [];

    if (isMachine) {
      if (u.user && (u.session_active || u.shutdown_remaining > 0)) rows.push([t.user, esc(u.user)]);
      if (u.session_active && u.session_start) {
        rows.push([t.runtime, `<span data-start="${u.session_start}">–</span>`]);
      }
      if (u.shutdown_remaining > 0) rows.push([t.cooldown, `${u.shutdown_remaining} s`]);
      if (u.last_cost != null) rows.push([t.lastCost, `${Number(u.last_cost).toFixed(2)} €`]);
      if (u.last_balance != null) rows.push([t.balance, `${Number(u.last_balance).toFixed(2)} €`]);
      rows.push([t.type, esc(t.types[u.machine_type] || u.machine_type)]);
    } else if (u.last_allowed != null) {
      rows.push([t.lastAccess, u.last_allowed ? t.granted : `<span class="bad">${esc(t.denied)}</span>`]);
    }

    rows.push([t.power, this._stateText(u.power === null ? null : u.power ? t.on : t.off, u.power === null)]);
    if (u.interlocks?.length) {
      rows.push([
        t.interlock,
        u.interlocks
          .map((i) => `<span class="${i.closed ? "" : "bad"}" title="${esc(i.entity_id)}">${esc(i.closed ? t.closed : t.open)}</span>`)
          .join(" · "),
      ]);
    }
    if (u.reader_online != null) {
      rows.push([t.reader, this._stateText(u.reader_online ? t.online : t.offline, !u.reader_online)]);
    }
    if (u.pending_bookings > 0) rows.push([t.pending, `<span class="bad">${u.pending_bookings}</span>`]);

    const busy = (action) => (this._busy.has(`${u.id}:${action}`) ? "disabled" : "");
    const actions = [];
    if (isMachine) {
      if (u.session_active) {
        actions.push(`<button class="primary" data-action="stop_session" data-unit="${esc(u.id)}" ${busy("stop_session")}>${esc(t.stopSession)}</button>`);
      } else if (u.shutdown_remaining > 0) {
        actions.push(`<button data-action="stop_session" data-unit="${esc(u.id)}" ${busy("stop_session")}>${esc(t.endCooldown)}</button>`);
      }
      actions.push(this._toggle(u, "admin", t.admin, u.admin, u.session_active));
    } else {
      actions.push(`<button class="primary" data-action="open_door" data-unit="${esc(u.id)}" ${busy("open_door")}>${esc(t.openDoor)}</button>`);
    }
    actions.push(this._toggle(u, "out_of_order", t.outOfOrder, u.out_of_order, false));
    if (u.device_id) {
      actions.push(`<button class="link" data-nav="/config/devices/device/${esc(u.device_id)}">${esc(t.device)} ›</button>`);
    }

    const [line1, line2] = u.display || ["", ""];
    return `
      <ha-card class="unit ${u.reader_online === false ? "offline" : ""}">
        <div class="head">
          <ha-icon icon="${isMachine ? "mdi:cog-outline" : "mdi:door"}"></ha-icon>
          <div class="name">
            <div class="title">${esc(u.name)}</div>
            <div class="sub">${esc(isMachine ? t.machine : t.door)} · Unit ${esc(u.unit_id)}</div>
          </div>
          <span class="badge" style="--badge:${color}">${esc(u.reader_online === false ? t.offline : statusLabel)}</span>
        </div>
        <div class="lcd" aria-label="Display"><div>${esc(String(line1).padEnd(16, " "))}</div><div>${esc(String(line2).padEnd(16, " "))}</div></div>
        <div class="rows">${rows.map(([k, v]) => `<div class="row"><span>${esc(k)}</span><span>${v}</span></div>`).join("")}</div>
        <div class="actions">${actions.join("")}</div>
      </ha-card>`;
  }

  _stateText(text, bad) {
    return text === null ? `<span class="bad">${esc(this._t.unavailable)}</span>` : `<span class="${bad ? "bad" : ""}">${esc(text)}</span>`;
  }

  _toggle(u, action, label, active, disabled) {
    const busy = this._busy.has(`${u.id}:${action}`);
    return `<button class="toggle ${active ? "on" : ""}" data-action="${action}" data-unit="${esc(u.id)}" data-value="${active ? "false" : "true"}" ${busy || disabled ? "disabled" : ""}>
      <ha-icon icon="${active ? "mdi:toggle-switch" : "mdi:toggle-switch-off-outline"}"></ha-icon>${esc(label)}</button>`;
  }

  _tickDurations() {
    const now = Date.now() / 1000;
    this.shadowRoot?.querySelectorAll("[data-start]").forEach((el) => {
      el.textContent = formatDuration(now - Number(el.dataset.start));
    });
  }

  _onClick(ev) {
    const nav = ev.target.closest("[data-nav]");
    if (nav) {
      history.pushState(null, "", nav.dataset.nav);
      window.dispatchEvent(new CustomEvent("location-changed"));
      return;
    }
    const button = ev.target.closest("button[data-action]");
    if (!button || button.disabled) return;
    const { action, unit } = button.dataset;
    const value = button.dataset.value === undefined ? undefined : button.dataset.value === "true";
    if (action === "stop_session") {
      const u = this._units.find((x) => x.id === unit);
      if (u?.session_active) {
        const text = this._t.confirmStop.replace("{user}", u.user || "?").replace("{name}", u.name);
        if (!window.confirm(text)) return;
      }
    }
    this._action(unit, action, value);
  }
}

const STYLE = `
  :host {
    display: block;
    min-height: 100vh;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
  }
  .toolbar {
    display: flex;
    align-items: center;
    height: var(--header-height, 56px);
    padding: 0 12px;
    background: var(--app-header-background-color, var(--primary-color));
    color: var(--app-header-text-color, var(--text-primary-color, #fff));
    border-bottom: var(--app-header-border-bottom, none);
    box-sizing: border-box;
  }
  .main-title { margin-left: 12px; font-size: 20px; font-weight: 400; }
  .content { padding: 16px; max-width: 1400px; margin: 0 auto; box-sizing: border-box; }
  .empty { padding: 48px 16px; text-align: center; color: var(--secondary-text-color); }
  .banner.error {
    padding: 12px 16px; margin-bottom: 16px; border-radius: 8px;
    background: rgba(219, 68, 55, 0.12); color: var(--error-color, #db4437);
  }
  .summary { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
  .chip {
    padding: 4px 12px; border-radius: 16px; font-size: 14px;
    background: color-mix(in srgb, var(--chip) 15%, transparent);
    color: var(--primary-text-color);
    border: 1px solid color-mix(in srgb, var(--chip) 40%, transparent);
  }
  .chip.muted { opacity: 0.55; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(320px, 100%), 1fr)); gap: 16px; }
  .unit { padding: 16px; display: flex; flex-direction: column; gap: 12px; box-sizing: border-box; min-width: 0; }
  .unit.offline { opacity: 0.75; }
  .head { display: flex; align-items: center; gap: 12px; }
  .head ha-icon { color: var(--secondary-text-color); }
  .name { flex: 1; min-width: 0; }
  .title { font-size: 16px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .sub { font-size: 13px; color: var(--secondary-text-color); }
  .badge {
    padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; white-space: nowrap;
    color: var(--badge); background: color-mix(in srgb, var(--badge) 15%, transparent);
  }
  .lcd {
    font-family: "Roboto Mono", ui-monospace, monospace; font-size: 15px; line-height: 1.35;
    white-space: pre; padding: 8px 12px; border-radius: 6px; align-self: flex-start;
    background: #1d2b12; color: #b8f36b; letter-spacing: 0.5px;
    box-shadow: inset 0 0 0 2px rgba(0, 0, 0, 0.35);
  }
  .rows { display: flex; flex-direction: column; gap: 4px; font-size: 14px; }
  .row { display: flex; justify-content: space-between; gap: 12px; }
  .row > span:first-child { color: var(--secondary-text-color); }
  .row > span:last-child { text-align: right; }
  .bad { color: var(--error-color, #db4437); }
  .actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: auto; }
  button {
    display: inline-flex; align-items: center; gap: 4px; cursor: pointer;
    font: inherit; font-size: 14px; padding: 6px 12px; border-radius: 18px;
    border: 1px solid var(--divider-color, rgba(0,0,0,0.12));
    background: transparent; color: var(--primary-text-color);
  }
  button:hover:not([disabled]) { background: color-mix(in srgb, var(--primary-color) 8%, transparent); }
  button[disabled] { opacity: 0.5; cursor: default; }
  button.primary { background: var(--primary-color); border-color: var(--primary-color); color: var(--text-primary-color, #fff); }
  button.toggle ha-icon { --mdc-icon-size: 20px; color: var(--secondary-text-color); }
  button.toggle.on ha-icon { color: var(--primary-color); }
  button.link { border-color: transparent; color: var(--primary-color); margin-left: auto; }
  @media (max-width: 600px) { .content { padding: 8px; } .grid { grid-template-columns: minmax(0, 1fr); } }
`;

if (!customElements.get("makerlink-panel")) {
  customElements.define("makerlink-panel", MakerLinkPanel);
}
