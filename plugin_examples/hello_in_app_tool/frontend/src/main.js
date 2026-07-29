import ToolView from "./ToolView.vue";

const TOOL_ID = "hello-in-app";
const SDK_VERSION = 1;
const sdk = window.DatalabToolSDK;

if (!sdk || sdk.version !== SDK_VERSION) {
  throw new Error(`Tool ${TOOL_ID} requires datalab frontend SDK ${SDK_VERSION}.`);
}

sdk.register({
  id: TOOL_ID,
  sdkVersion: SDK_VERSION,
  component: ToolView,
});
