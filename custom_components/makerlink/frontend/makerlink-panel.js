// MakerLink sidebar panel: overview of all configured readers (machines & doors).
// Plain web component, no build step. Data comes live via the websocket
// command "makerlink/subscribe" (see ws_api.py), actions via "makerlink/action".

const TEXT = {
  de: {
    title: "MakerLink",
    loading: "Lade Reader…",
    notConfigured: "MakerLink ist noch nicht eingerichtet. Einstellungen → Geräte & Dienste → Integration hinzufügen → MakerLink.",
    noUnits: "Noch keine Maschinen oder Türen angelegt.",
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
    addReader: "Reader hinzufügen",
    newReaders: "Neue Reader",
    newReadersHint: "Diese Reader sind in Home Assistant angemeldet, aber noch keiner Maschine oder Tür zugeordnet.",
    adminOnly: "Ein Administrator muss die Reader einrichten.",
    setup: "Einrichten",
    identify: "Identifizieren",
    identifyShown: "Der Reader zeigt jetzt „HIER BIN ICH“ (10 s).",
    noRelay: "kein Relais gefunden",
    noDisplay: "kein Display",
    firmware: "Firmware",
    pendingEsphome: "In ESPHome gefunden, aber noch nicht bestätigt: {names}. Dort bei „Gefundene Geräte“ auf „Hinzufügen“ klicken, dann erscheint der Reader hier.",
    toEsphome: "Zu ESPHome ›",
    edit: "Bearbeiten",
    remove: "Entfernen",
    confirmRemove: "{name} entfernen? Der Reader erscheint danach wieder unter „Neue Reader“.",
    formAdd: "Reader einrichten",
    formEdit: "Bearbeiten",
    fName: "Name / Beschreibung",
    fKind: "Funktion",
    fUnit: "Unit-ID",
    fUnitHint: "9999 ist die Test-ID und darf mehrfach vergeben werden.",
    fType: "Abrechnung",
    fPower: "Schaltziel",
    fPowerAuto: "Relais am Reader",
    fKindNote: "Beim Wechsel zwischen Maschine und Tür werden die Einstellungen der Einheit zurückgesetzt (Nachlauf, Mindestguthaben, …).",
    save: "Speichern",
    cancel: "Abbrechen",
    close: "Schließen",
    errors: {
      unit_exists: "Diese Unit-ID ist schon vergeben.",
      reader_in_use: "Dieser Reader gehört schon zu einer Einheit.",
      no_power_target: "Dieser Reader hat kein Relais. Bitte ein Schaltziel wählen.",
      unit_busy: "Die Einheit ist gerade in Benutzung (Session oder offene Buchung).",
      invalid_devicename: "Nur Kleinbuchstaben, Ziffern und Bindestrich, höchstens 31 Zeichen.",
      devicename_exists: "Dieser Gerätename existiert in ESPHome schon.",
      invalid_unit_id: "Die Unit-ID muss zwischen 1 und 99999 liegen.",
    },
    prepTitle: "Neuen Reader vorbereiten",
    prepSteps: [
      "Hardware und Gerätename wählen und die YAML-Datei kopieren.",
      "In ESPHome ein neues Gerät mit genau diesem Namen anlegen („Leere Konfiguration“), den Inhalt ersetzen und installieren. Das erste Mal per USB.",
      "In Home Assistant bei der ESPHome-Integration das gefundene Gerät hinzufügen.",
      "Der Reader erscheint dann hier unter „Neue Reader“. Dort Funktion (Maschine oder Tür), Name und Unit-ID festlegen.",
    ],
    prepOnce: "Einmalig vorab: Der Inhalt von esphome/ aus dem Repository liegt in /config/esphome/ und secrets.yaml ist ausgefüllt (siehe README).",
    fHardware: "Hardware",
    fDevicename: "Gerätename",
    fFriendly: "Beschreibung (optional)",
    copy: "Kopieren",
    copied: "Kopiert",
    download: "Herunterladen",
    saveAs: "Dateiname",
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
    noUnits: "No machines or doors yet.",
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
    addReader: "Add reader",
    newReaders: "New readers",
    newReadersHint: "These readers are registered in Home Assistant but not assigned to a machine or door yet.",
    adminOnly: "An administrator has to set up the readers.",
    setup: "Set up",
    identify: "Identify",
    identifyShown: "The reader now shows “HIER BIN ICH” (10 s).",
    noRelay: "no relay found",
    noDisplay: "no display",
    firmware: "Firmware",
    pendingEsphome: "Found in ESPHome but not confirmed yet: {names}. Click “Add” under “Discovered” there and the reader shows up here.",
    toEsphome: "Go to ESPHome ›",
    edit: "Edit",
    remove: "Remove",
    confirmRemove: "Remove {name}? The reader will show up under “New readers” again.",
    formAdd: "Set up reader",
    formEdit: "Edit",
    fName: "Name / description",
    fKind: "Function",
    fUnit: "Unit ID",
    fUnitHint: "9999 is the test ID and may be used several times.",
    fType: "Billing",
    fPower: "Switch target",
    fPowerAuto: "Relay on the reader",
    fKindNote: "Switching between machine and door resets the settings of the unit (cooldown, minimum balance, …).",
    save: "Save",
    cancel: "Cancel",
    close: "Close",
    errors: {
      unit_exists: "This unit ID is already taken.",
      reader_in_use: "This reader already belongs to a unit.",
      no_power_target: "This reader has no relay. Please choose a switch target.",
      unit_busy: "The unit is in use right now (session or pending booking).",
      invalid_devicename: "Lowercase letters, digits and hyphen only, at most 31 characters.",
      devicename_exists: "This device name already exists in ESPHome.",
      invalid_unit_id: "The unit ID must be between 1 and 99999.",
    },
    prepTitle: "Prepare a new reader",
    prepSteps: [
      "Choose the hardware and a device name, then copy the YAML file.",
      "In ESPHome create a new device with exactly that name (“Empty configuration”), replace its content and install. The first time over USB.",
      "In Home Assistant add the discovered device in the ESPHome integration.",
      "The reader then shows up here under “New readers”. Set function (machine or door), name and unit ID there.",
    ],
    prepOnce: "Once beforehand: the content of esphome/ from the repository is in /config/esphome/ and secrets.yaml is filled in (see README).",
    fHardware: "Hardware",
    fDevicename: "Device name",
    fFriendly: "Description (optional)",
    copy: "Copy",
    copied: "Copied",
    download: "Download",
    saveAs: "File name",
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
    this._readers = [];
    this._esphomePending = [];
    this._optionsCache = null;
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
    // New ESPHome discoveries have no registry event: look again from time to time.
    this._poll = setInterval(() => this._refresh(), 5000);
    if (this._hass) {
      this._renderShell();
      this._subscribe();
    }
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    clearInterval(this._poll);
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
      (msg) => this._apply(msg),
      { type: "makerlink/subscribe" }
    );
    this._unsub.catch((err) => {
      this._error = err?.message || String(err);
      this._unsub = null;
      this._render();
    });
  }

  _apply(msg) {
    const key = JSON.stringify(msg);
    if (this._loaded && key === this._lastKey) return;
    // While the config entry reloads after a save the unit list is briefly empty.
    if (Date.now() < (this._holdUntil || 0) && !(msg.units || []).length && this._units.length) return;
    this._lastKey = key;
    this._units = msg.units || [];
    this._readers = msg.readers || [];
    this._esphomePending = msg.esphome_pending || [];
    this._configured = msg.configured !== false;
    this._loaded = true;
    this._error = null;
    this._render();
  }

  async _refresh() {
    if (!this._hass || !this.isConnected || !this._loaded) return;
    try {
      this._apply(await this._hass.callWS({ type: "makerlink/units" }));
    } catch (err) {
      /* the subscription reports errors */
    }
  }

  get _admin() {
    return !!this._hass?.user?.is_admin;
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
        <button class="toolbar-add" data-ui="prepare" hidden><ha-icon icon="mdi:plus"></ha-icon>${esc(this._t.addReader)}</button>
      </div>
      <div class="content"></div>
      <div class="overlay"></div>`;
    this.shadowRoot.querySelector(".toolbar").addEventListener("click", (ev) => this._onClick(ev));
    this.shadowRoot.querySelector(".content").addEventListener("click", (ev) => this._onClick(ev));
    this.shadowRoot.querySelector(".overlay").addEventListener("click", (ev) => this._onOverlayClick(ev));
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
    if (this._notice) html += `<div class="banner info">${esc(this._notice)}</div>`;
    if (!this._loaded) {
      html += `<div class="empty">${esc(t.loading)}</div>`;
    } else if (!this._configured) {
      html += `<div class="empty">${esc(t.notConfigured)}</div>`;
    } else {
      html += this._renderOnboarding();
      if (this._units.length) {
        html += this._renderSummary();
        html += `<div class="grid">${this._units.map((u) => this._renderUnit(u)).join("")}</div>`;
      } else if (!this._readers.length) {
        html += `<div class="empty">${esc(t.noUnits)}${
          this._admin ? `<div><button class="primary" data-ui="prepare">${esc(t.addReader)}</button></div>` : ""
        }</div>`;
      }
    }
    const add = this.shadowRoot.querySelector(".toolbar-add");
    if (add) add.hidden = !(this._admin && this._configured && this._loaded);
    content.innerHTML = html;
    this._tickDurations();
  }

  _renderOnboarding() {
    const t = this._t;
    let html = "";
    if (this._esphomePending.length) {
      html += `<div class="banner info">${esc(t.pendingEsphome.replace("{names}", this._esphomePending.join(", ")))}
        <button data-nav="/config/integrations/integration/esphome">${esc(t.toEsphome)}</button></div>`;
    }
    if (this._readers.length) {
      html += `<div class="section"><div class="section-title">${esc(t.newReaders)}</div>
        <div class="hint">${esc(this._admin ? t.newReadersHint : t.adminOnly)}</div>
        <div class="grid">${this._readers.map((r) => this._renderReader(r)).join("")}</div></div>`;
    }
    return html;
  }

  _renderReader(r) {
    const t = this._t;
    const notes = [];
    if (r.firmware) notes.push(`${esc(t.firmware)} ${esc(r.firmware)}`);
    if (!r.has_relay) notes.push(`<span class="bad">${esc(t.noRelay)}</span>`);
    if (!r.has_display) notes.push(esc(t.noDisplay));
    const actions = this._admin
      ? `<button class="primary" data-ui="setup" data-reader="${esc(r.device_id)}">${esc(t.setup)}</button>
         ${r.has_display && r.online ? `<button data-ui="identify" data-reader="${esc(r.device_id)}">${esc(t.identify)}</button>` : ""}`
      : "";
    const color = r.online ? "var(--success-color, #43a047)" : "var(--disabled-text-color, #9e9e9e)";
    return `
      <ha-card class="unit ${r.online ? "" : "offline"}">
        <div class="head">
          <ha-icon icon="mdi:card-account-details-outline"></ha-icon>
          <div class="name"><div class="title">${esc(r.name)}</div><div class="sub">${notes.join(" · ")}</div></div>
          <span class="badge" style="--badge:${color}">${esc(r.online ? t.online : t.offline)}</span>
        </div>
        <div class="actions">${actions}</div>
      </ha-card>`;
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
    if (this._admin) {
      actions.push(`<button class="ghost" data-ui="edit" data-unit="${esc(u.id)}">${esc(t.edit)}</button>`);
    }
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

  // ----- onboarding: dialogs ----------------------------------------------------

  _ui(d) {
    if (d.ui === "prepare") this._openPrepare();
    else if (d.ui === "setup") this._openUnitForm({ reader: this._readers.find((r) => r.device_id === d.reader) });
    else if (d.ui === "edit") this._openUnitForm({ unit: this._units.find((u) => u.id === d.unit) });
    else if (d.ui === "identify") this._identify(d.reader);
  }

  _fail(err) {
    this._error = this._t.errors[err?.code] || err?.message || String(err);
    this._render();
  }

  _showDialog(html) {
    const overlay = this.shadowRoot.querySelector(".overlay");
    overlay.innerHTML = `<dialog>${html}</dialog>`;
    const dialog = overlay.querySelector("dialog");
    dialog.addEventListener("close", () => {
      overlay.innerHTML = "";
    });
    dialog.showModal();
    return dialog;
  }

  _closeDialog() {
    this.shadowRoot.querySelector(".overlay dialog")?.close();
  }

  _onOverlayClick(ev) {
    const button = ev.target.closest("[data-dlg]");
    if (!button || button.disabled) return;
    const action = button.dataset.dlg;
    if (action === "close") this._closeDialog();
    else if (action === "copy") this._copyYaml(button);
    else if (action === "download") this._downloadYaml();
    else if (action === "remove") this._removeUnit();
  }

  async _identify(readerId) {
    try {
      await this._hass.callWS({ type: "makerlink/identify", reader_device: readerId });
      this._notice = this._t.identifyShown;
      this._render();
      clearTimeout(this._noticeTimer);
      this._noticeTimer = setTimeout(() => {
        this._notice = null;
        this._render();
      }, 10000);
    } catch (err) {
      this._fail(err);
    }
  }

  // Step 1 of a new reader: device YAML with a free name, ready to paste into ESPHome.
  async _openPrepare() {
    let opts;
    try {
      opts = await this._hass.callWS({ type: "makerlink/options" });
    } catch (err) {
      this._fail(err);
      return;
    }
    const t = this._t;
    this._yaml = null;
    const dialog = this._showDialog(`
      <h2>${esc(t.prepTitle)}</h2>
      <ol class="steps">${t.prepSteps.map((text) => `<li>${esc(text)}</li>`).join("")}</ol>
      <div class="hint">${esc(t.prepOnce)}</div>
      <label>${esc(t.fHardware)}
        <select name="hardware">${opts.hardware.map((h) => `<option value="${esc(h.id)}">${esc(h.label)}</option>`).join("")}</select>
      </label>
      <label>${esc(t.fDevicename)}
        <input name="devicename" value="${esc(opts.suggested_devicename)}" autocomplete="off" spellcheck="false">
      </label>
      <label>${esc(t.fFriendly)}
        <input name="friendly_name" autocomplete="off">
      </label>
      <div class="error" data-role="error"></div>
      <div class="filename" data-role="filename"></div>
      <textarea readonly rows="10" spellcheck="false" data-role="yaml"></textarea>
      <div class="dlg-actions">
        <button class="primary" data-dlg="copy" disabled>${esc(t.copy)}</button>
        <button data-dlg="download" disabled>${esc(t.download)}</button>
        <button data-dlg="close">${esc(t.close)}</button>
      </div>`);
    const q = (sel) => dialog.querySelector(sel);
    let timer;
    const generate = async () => {
      const msg = {
        type: "makerlink/reader_yaml",
        hardware: q("[name=hardware]").value,
        devicename: q("[name=devicename]").value.trim(),
      };
      const friendly = q("[name=friendly_name]").value.trim();
      if (friendly) msg.friendly_name = friendly;
      try {
        this._yaml = await this._hass.callWS(msg);
        q("[data-role=error]").textContent = "";
        q("[data-role=filename]").textContent = `${t.saveAs}: ${this._yaml.filename}`;
        q("[data-role=yaml]").value = this._yaml.yaml;
      } catch (err) {
        this._yaml = null;
        q("[data-role=error]").textContent = t.errors[err?.code] || err?.message || String(err);
        q("[data-role=filename]").textContent = "";
        q("[data-role=yaml]").value = "";
      }
      dialog.querySelectorAll("[data-dlg=copy], [data-dlg=download]").forEach((b) => {
        b.disabled = !this._yaml;
      });
    };
    dialog.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(generate, 300);
    });
    dialog.addEventListener("change", generate);
    generate();
  }

  async _copyYaml(button) {
    const text = this._yaml?.yaml;
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      // No clipboard API on plain http: select the text and use the old way.
      const area = this.shadowRoot.querySelector("textarea[data-role=yaml]");
      area.select();
      document.execCommand("copy");
    }
    button.textContent = this._t.copied;
    setTimeout(() => {
      button.textContent = this._t.copy;
    }, 1500);
  }

  _downloadYaml() {
    if (!this._yaml) return;
    const url = URL.createObjectURL(new Blob([this._yaml.yaml], { type: "text/yaml" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = this._yaml.filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  // Add (reader given) or edit (unit given): name, function, unit ID, optionally the switch target.
  async _openUnitForm({ reader, unit }) {
    if (!reader && !unit) return;
    let opts;
    try {
      opts = await this._hass.callWS({ type: "makerlink/options" });
    } catch (err) {
      this._fail(err);
      return;
    }
    const t = this._t;
    const editing = !!unit;
    this._editUnit = unit || null;
    const kind = unit?.kind || "machine";
    const power = unit?.power_entity || "";
    const switches = [...opts.switches];
    if (power && !switches.some((x) => x.entity_id === power)) switches.unshift({ entity_id: power, name: power });
    const autoRelay = !editing && reader.has_relay;
    const powerOptions =
      `<option value="">${esc(autoRelay ? t.fPowerAuto : "–")}</option>` +
      switches
        .map(
          (x) =>
            `<option value="${esc(x.entity_id)}" ${x.entity_id === power ? "selected" : ""}>${esc(x.name)} (${esc(x.entity_id)})</option>`
        )
        .join("");
    const radio = (value, label) =>
      `<label class="radio"><input type="radio" name="kind" value="${value}" ${kind === value ? "checked" : ""}>${esc(label)}</label>`;
    const dialog = this._showDialog(`
      <h2>${esc(editing ? `${t.formEdit}: ${unit.name}` : `${t.formAdd}: ${reader.name}`)}</h2>
      <form>
        <label>${esc(t.fName)}
          <input name="name" required maxlength="64" value="${esc(unit?.name || reader.name)}" autocomplete="off">
        </label>
        <fieldset><legend>${esc(t.fKind)}</legend>${radio("machine", t.machine)}${radio("door", t.door)}</fieldset>
        <div class="hint" data-role="kindnote" hidden>${esc(t.fKindNote)}</div>
        <label>${esc(t.fUnit)}
          <input name="unit_id" type="number" min="1" max="99999" step="1" required value="${esc(unit ? unit.unit_id : opts.test_unit_id)}">
          <span class="hint">${esc(t.fUnitHint)}</span>
        </label>
        <label data-for="machine">${esc(t.fType)}
          <select name="machine_type">${opts.machine_types
            .map((m) => `<option value="${esc(m)}" ${m === (unit?.machine_type || "machine") ? "selected" : ""}>${esc(t.types[m] || m)}</option>`)
            .join("")}</select>
        </label>
        <label>${esc(t.fPower)}
          <select name="power_entity" ${autoRelay || editing ? "" : "required"}>${powerOptions}</select>
        </label>
        <div class="error" data-role="error"></div>
        <div class="dlg-actions">
          <button class="primary" type="submit">${esc(t.save)}</button>
          <button type="button" data-dlg="close">${esc(t.cancel)}</button>
          ${editing ? `<button type="button" class="danger" data-dlg="remove">${esc(t.remove)}</button>` : ""}
        </div>
      </form>`);
    const form = dialog.querySelector("form");
    const sync = () => {
      const value = form.elements.kind.value;
      dialog.querySelectorAll("[data-for]").forEach((el) => {
        el.hidden = el.dataset.for !== value;
      });
      dialog.querySelector("[data-role=kindnote]").hidden = !(editing && value !== kind);
    };
    form.addEventListener("change", sync);
    sync();
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const data = new FormData(form);
      const msg = {
        type: editing ? "makerlink/unit_update" : "makerlink/unit_add",
        name: String(data.get("name")).trim(),
        kind: data.get("kind"),
        unit_id: Number(data.get("unit_id")),
      };
      if (editing) msg.unit = unit.id;
      else msg.reader_device = reader.device_id;
      if (msg.kind === "machine") msg.machine_type = data.get("machine_type");
      if (data.get("power_entity")) msg.power_entity = data.get("power_entity");
      const save = form.querySelector("[type=submit]");
      save.disabled = true;
      try {
        await this._hass.callWS(msg);
        this._holdUntil = Date.now() + 4000;
        this._closeDialog();
        this._refresh();
      } catch (err) {
        dialog.querySelector("[data-role=error]").textContent = t.errors[err?.code] || err?.message || String(err);
        save.disabled = false;
      }
    });
  }

  async _removeUnit() {
    const unit = this._editUnit;
    if (!unit || !window.confirm(this._t.confirmRemove.replace("{name}", unit.name))) return;
    try {
      await this._hass.callWS({ type: "makerlink/unit_remove", unit: unit.id });
      this._holdUntil = Date.now() + 4000;
      this._closeDialog();
      this._refresh();
    } catch (err) {
      this._closeDialog();
      this._fail(err);
    }
  }

  _onClick(ev) {
    const ui = ev.target.closest("[data-ui]");
    if (ui) {
      this._ui(ui.dataset);
      return;
    }
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
  .banner.info {
    display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
    padding: 12px 16px; margin-bottom: 16px; border-radius: 8px;
    background: color-mix(in srgb, var(--info-color, #039be5) 14%, transparent);
  }
  .section { margin-bottom: 24px; }
  .section-title { font-size: 18px; font-weight: 500; }
  .hint { font-size: 13px; color: var(--secondary-text-color); margin: 2px 0 8px; }
  button.ghost { border-color: transparent; color: var(--secondary-text-color); }
  button.danger { color: var(--error-color, #db4437); border-color: var(--error-color, #db4437); margin-left: auto; }
  .toolbar button.toolbar-add {
    margin-left: auto; color: inherit; border-color: color-mix(in srgb, currentColor 45%, transparent);
  }
  .toolbar button.toolbar-add[hidden] { display: none; }
  .empty > div { margin-top: 16px; }
  dialog {
    width: min(560px, calc(100vw - 32px)); max-height: calc(100vh - 32px); box-sizing: border-box;
    padding: 20px; border: none; border-radius: 12px; overflow: auto;
    background: var(--card-background-color, var(--primary-background-color)); color: var(--primary-text-color);
  }
  dialog::backdrop { background: rgba(0, 0, 0, 0.5); }
  dialog h2 { margin: 0 0 12px; font-size: 20px; font-weight: 500; }
  dialog label { display: flex; flex-direction: column; gap: 4px; margin: 12px 0; font-size: 14px; color: var(--secondary-text-color); }
  dialog label[hidden] { display: none; }
  dialog input:not([type=radio]), dialog select, dialog textarea {
    font: inherit; padding: 8px; border-radius: 6px; box-sizing: border-box; width: 100%;
    border: 1px solid var(--divider-color, rgba(0,0,0,0.2));
    background: var(--secondary-background-color, transparent); color: var(--primary-text-color);
  }
  dialog textarea { font-family: ui-monospace, monospace; font-size: 12px; resize: vertical; }
  dialog fieldset { border: 1px solid var(--divider-color, rgba(0,0,0,0.2)); border-radius: 6px; margin: 12px 0; display: flex; gap: 24px; }
  dialog legend { font-size: 13px; color: var(--secondary-text-color); padding: 0 4px; }
  dialog label.radio { flex-direction: row; align-items: center; gap: 6px; margin: 4px 0; color: var(--primary-text-color); }
  dialog .steps { margin: 0 0 8px; padding-left: 20px; font-size: 14px; }
  dialog .steps li { margin: 4px 0; }
  dialog .error { color: var(--error-color, #db4437); font-size: 14px; min-height: 1em; }
  dialog .filename { font-size: 13px; color: var(--secondary-text-color); margin-bottom: 4px; }
  .dlg-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
  @media (max-width: 600px) { .content { padding: 8px; } .grid { grid-template-columns: minmax(0, 1fr); } }
`;

if (!customElements.get("makerlink-panel")) {
  customElements.define("makerlink-panel", MakerLinkPanel);
}
