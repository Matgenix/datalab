// This file was edited with the assistance of an AI model and requires human review from the contributor.
import { launchTool } from "@/server_fetch_utils.js";

const ITEM_TABLE_IDS = Object.freeze({
  samples: "samples",
  startingMaterials: "inventory",
  equipment: "equipment",
  collectionItems: "collection-items",
});

export function parseToolLaunchUrl(url) {
  const parsedUrl = new URL(url, window.location.origin);
  if (
    !["http:", "https:"].includes(parsedUrl.protocol) ||
    parsedUrl.username ||
    parsedUrl.password
  ) {
    throw new Error("The tool returned an unsafe launch URL.");
  }
  return parsedUrl.href;
}

export function openToolPlaceholderTab() {
  const launchWindow = window.open("about:blank", "_blank");
  if (!launchWindow) {
    throw new Error(
      "The new tab was blocked by your browser. Allow pop-ups for this site and try again.",
    );
  }
  launchWindow.opener = null;
  return launchWindow;
}

export function isSupportedTool(tool) {
  return (
    (tool?.ui?.kind === "standalone" && ["same_tab", "new_tab"].includes(tool.ui.open_mode)) ||
    (tool?.ui?.kind === "in_app" &&
      ["same_tab", "new_tab"].includes(tool.ui.open_mode) &&
      tool.ui.sdk_version === 1 &&
      typeof tool.ui.entrypoint === "string")
  );
}

export function itemTableSelectionActions(tools, dataType) {
  const tableId = ITEM_TABLE_IDS[dataType];
  if (!tableId) {
    return [];
  }

  return tools.flatMap((tool) =>
    (tool.launch_actions || [])
      .filter(
        (action) =>
          action?.kind === "item-table-selection" &&
          Array.isArray(action.tables) &&
          action.tables.includes(tableId),
      )
      .map((action) => ({ action, tool })),
  );
}

export async function openTool(tool, router, query = undefined) {
  if (!isSupportedTool(tool)) {
    throw new Error("This tool requires an unsupported frontend integration.");
  }

  if (tool.ui.kind === "in_app") {
    const route = { name: "tool", params: { toolId: tool.id }, query };
    if (tool.ui.open_mode === "same_tab") {
      await router.push(route);
      return;
    }

    const launchWindow = openToolPlaceholderTab();
    launchWindow.location.replace(new URL(router.resolve(route).href, window.location.origin).href);
    return;
  }

  const launchWindow = tool.ui.open_mode === "new_tab" ? openToolPlaceholderTab() : null;
  try {
    const launch = await launchTool(tool.id);
    if (typeof launch.url !== "string") {
      throw new Error("The tool returned an unexpected launch result.");
    }
    const launchUrl = parseToolLaunchUrl(launch.url);
    if (launchWindow) {
      launchWindow.location.replace(launchUrl);
    } else {
      window.location.assign(launchUrl);
    }
  } catch (error) {
    launchWindow?.close();
    throw error;
  }
}

export async function openToolForItemSelection(tool, action, items, router) {
  if (tool?.ui?.kind !== "in_app" || action?.kind !== "item-table-selection") {
    throw new Error("This tool does not support an in-app table-selection action.");
  }

  const itemRefcodes = [...new Set(items.map((item) => item?.refcode))];
  if (itemRefcodes.some((refcode) => typeof refcode !== "string" || !refcode)) {
    throw new Error("Every selected item must have an immutable refcode.");
  }
  if (itemRefcodes.length < action.min_items || itemRefcodes.length > action.max_items) {
    throw new Error("The selected-item count is outside this tool action's limits.");
  }

  await openTool(tool, router, {
    action: action.id,
    items: itemRefcodes,
  });
}
