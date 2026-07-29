(function () {
  "use strict";

  const sdk = window.DatalabToolSDK;
  const vue = sdk?.vue;
  const TOOL_ID = "hello-in-app";
  const SDK_VERSION = 1;

  if (!sdk || sdk.version !== SDK_VERSION || !vue) {
    throw new Error(`Tool ${TOOL_ID} requires datalab frontend SDK ${SDK_VERSION}.`);
  }

  const ToolView = {
    name: "HelloInAppTool",
    data() {
      return {
        isLoading: true,
        loadError: null,
        displayName: "datalab user",
        sampleCount: 0
      };
    },
    mounted() {
      this.loadMessage();
    },
    methods: {
      async loadMessage() {
        try {
          const [currentUser, sampleResponse] = await Promise.all([
            sdk.api.get("/get-current-user/"),
            sdk.api.get("/samples/")
          ]);
          this.displayName = currentUser?.display_name || currentUser?.immutable_id || "datalab user";
          this.sampleCount = Array.isArray(sampleResponse?.samples) ? sampleResponse.samples.length : 0;
        } catch (error) {
          this.loadError = error instanceof Error ? error.message : String(error);
        } finally {
          this.isLoading = false;
        }
      }
    }
  };

  function render(_ctx, _cache) {
    const message = _ctx.isLoading
      ? "Loading..."
      : _ctx.loadError
        ? `Error: ${_ctx.loadError}`
        : `Hello ${_ctx.displayName}. You can access ${_ctx.sampleCount} sample(s).`;
    return vue.h("section", { class: "datalab-tool-hello-in-app hello-in-app-page px-3 py-3" }, [
      vue.h("h1", { class: "h3" }, "Hello in-app"),
      vue.h("p", { class: _ctx.loadError ? "text-danger" : "" }, message)
    ]);
  }

  ToolView.render = render;
  sdk.register({
    id: TOOL_ID,
    sdkVersion: SDK_VERSION,
    component: ToolView
  });
})();
