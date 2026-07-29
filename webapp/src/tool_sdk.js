// This file was edited with the assistance of an AI model and requires human review from the contributor.
import * as Vue from "vue";

import BokehPlot from "@/components/BokehPlot.vue";
import ChemicalFormula from "@/components/ChemicalFormula.vue";
import FormattedItemName from "@/components/FormattedItemName.vue";
import ItemSelect from "@/components/ItemSelect.vue";
import { API_URL } from "@/resources.js";
import { DialogService } from "@/services/DialogService.js";
import { toolApiGet, toolApiPost } from "@/server_fetch_utils.js";

export const TOOL_SDK_VERSION = 1;

const TOOL_ID_PATTERN = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;
const TOOL_ACTION_ID_PATTERN = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;
const MAX_SELECTED_ITEM_REFCODES = 100;
const registeredInAppTools = new Map();
const inAppToolLoads = new Map();
const expectedRegistrations = new Set();
let publicSdk = null;

function normalizeQueryValues(value, limit = Number.POSITIVE_INFINITY) {
  const values = Array.isArray(value) ? value : value == null ? [] : [value];
  const normalized = [];
  const seen = new Set();
  for (const candidate of values) {
    if (typeof candidate !== "string") {
      continue;
    }
    const value = candidate.trim();
    if (value && !seen.has(value)) {
      seen.add(value);
      normalized.push(value);
      if (normalized.length === limit) {
        break;
      }
    }
  }
  return normalized;
}

function registerInAppTool(definition) {
  const { id, sdkVersion, component } = definition || {};
  if (typeof id !== "string" || !TOOL_ID_PATTERN.test(id)) {
    throw new Error("An in-app tool must register its provider ID.");
  }
  if (sdkVersion !== TOOL_SDK_VERSION) {
    throw new Error(`In-app tool ${id} requires unsupported frontend SDK version ${sdkVersion}.`);
  }
  if ((typeof component !== "object" || component === null) && typeof component !== "function") {
    throw new Error(`In-app tool ${id} did not register a frontend component.`);
  }
  const loadingToolId = document.currentScript?.dataset?.DatalabToolId;
  if (!expectedRegistrations.has(id) || loadingToolId !== id) {
    throw new Error(`In-app tool ${id} was not requested by the datalab tool host.`);
  }
  if (registeredInAppTools.has(id)) {
    throw new Error(`In-app tool ${id} is already registered.`);
  }

  registeredInAppTools.set(id, Object.freeze({ id, sdkVersion, component }));
}

function providerBaseUrl(toolId) {
  const apiBase = new URL(`${API_URL.replace(/\/+$/, "")}/`, window.location.origin);
  return new URL(`tools/plugins/${encodeURIComponent(toolId)}/`, apiBase);
}

function resolveEntrypointUrl(tool) {
  const entrypoint = tool?.ui?.entrypoint;
  if (typeof entrypoint !== "string" || entrypoint.length === 0) {
    throw new Error(`In-app tool ${tool?.id || ""} has no frontend entrypoint.`);
  }

  const baseUrl = providerBaseUrl(tool.id);
  const entrypointUrl = new URL(entrypoint, baseUrl);
  if (
    entrypointUrl.origin !== baseUrl.origin ||
    !entrypointUrl.pathname.startsWith(baseUrl.pathname)
  ) {
    throw new Error(`In-app tool ${tool.id} has an unsafe frontend entrypoint.`);
  }
  return entrypointUrl.href;
}

function loadInAppToolScript(tool) {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    let settled = false;
    const finish = (callback, value, removeScript = false) => {
      if (settled) {
        return;
      }
      settled = true;
      window.clearTimeout(timeout);
      expectedRegistrations.delete(tool.id);
      if (removeScript) {
        script.remove();
      }
      callback(value);
    };

    script.async = true;
    script.crossOrigin = "use-credentials";
    script.dataset.DatalabToolId = tool.id;
    script.src = resolveEntrypointUrl(tool);
    expectedRegistrations.add(tool.id);
    script.addEventListener("load", () => {
      const registration = registeredInAppTools.get(tool.id);
      if (!registration) {
        finish(
          reject,
          new Error(`In-app tool ${tool.id} loaded without registering a component.`),
          true,
        );
        return;
      }
      finish(resolve, registration.component);
    });
    script.addEventListener("error", () => {
      finish(
        reject,
        new Error(`Unable to load the frontend bundle for ${tool.name || tool.id}.`),
        true,
      );
    });
    const timeout = window.setTimeout(() => {
      finish(
        reject,
        new Error(`Timed out while loading the frontend bundle for ${tool.name || tool.id}.`),
        true,
      );
    }, 15000);
    document.head.appendChild(script);
  });
}

export async function loadInAppTool(tool) {
  if (
    tool?.ui?.kind !== "in_app" ||
    !["same_tab", "new_tab"].includes(tool.ui.open_mode) ||
    tool.ui.sdk_version !== TOOL_SDK_VERSION
  ) {
    throw new Error("This tool requires an unsupported frontend integration.");
  }

  const registration = registeredInAppTools.get(tool.id);
  if (registration) {
    return registration.component;
  }

  if (!inAppToolLoads.has(tool.id)) {
    const load = loadInAppToolScript(tool).catch((error) => {
      inAppToolLoads.delete(tool.id);
      throw error;
    });
    inAppToolLoads.set(tool.id, load);
  }
  return inAppToolLoads.get(tool.id);
}

export function installDatalabToolSdk(router) {
  if (publicSdk) {
    return publicSdk;
  }

  const components = Object.freeze({
    BokehPlot,
    ChemicalFormula,
    FormattedItemName,
    ItemSelect,
  });
  const api = Object.freeze({
    baseUrl: API_URL,
    get: toolApiGet,
    post: toolApiPost,
  });
  const navigation = Object.freeze({
    currentRoute: () => router.currentRoute.value,
    push: (location) => router.push(location),
    replace: (location) => router.replace(location),
  });
  const selection = Object.freeze({
    current: () => {
      const query = router.currentRoute.value.query;
      const actionId = normalizeQueryValues(query.action, 1)[0] || null;
      return Object.freeze({
        actionId: actionId && TOOL_ACTION_ID_PATTERN.test(actionId) ? actionId : null,
        itemRefcodes: Object.freeze(normalizeQueryValues(query.items, MAX_SELECTED_ITEM_REFCODES)),
      });
    },
    replaceItemRefcodes: (refcodes) => {
      const route = router.currentRoute.value;
      const query = { ...route.query };
      const normalized = normalizeQueryValues(refcodes, MAX_SELECTED_ITEM_REFCODES);
      if (normalized.length) {
        query.items = normalized;
      } else {
        delete query.items;
      }
      return router.replace({
        name: route.name,
        params: route.params,
        query,
      });
    },
  });
  const dialogs = Object.freeze({
    alert: (options) => DialogService.alert(options),
    confirm: (options) => DialogService.confirm(options),
    error: (options) => DialogService.error(options),
  });

  publicSdk = Object.freeze({
    version: TOOL_SDK_VERSION,
    vue: Vue,
    components,
    api,
    navigation,
    selection,
    dialogs,
    register: registerInAppTool,
  });

  if (
    Object.prototype.hasOwnProperty.call(window, "DatalabToolSDK") &&
    window.DatalabToolSDK !== publicSdk
  ) {
    throw new Error("The datalab tool SDK global is already defined.");
  }
  Object.defineProperty(window, "DatalabToolSDK", {
    configurable: false,
    enumerable: false,
    writable: false,
    value: publicSdk,
  });
  return publicSdk;
}
