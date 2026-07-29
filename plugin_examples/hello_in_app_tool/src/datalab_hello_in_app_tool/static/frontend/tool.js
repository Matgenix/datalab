(function(vue) {
	//#region \0plugin-vue:export-helper
	var _plugin_vue_export_helper_default = (sfc, props) => {
		const target = sfc.__vccOpts || sfc;
		for (const [key, val] of props) target[key] = val;
		return target;
	};
	//#endregion
	//#region src/ToolView.vue
	var sdk = window.datalabToolSdk;
	var _sfc_main = {
		name: "HelloInAppTool",
		data() {
			return { message: "Loading..." };
		},
		mounted() {
			this.loadMessage();
		},
		methods: { async loadMessage() {
			try {
				const [currentUser, sampleResponse] = await Promise.all([sdk.api.get("/get-current-user/"), sdk.api.get("/samples/")]);
				const name = currentUser?.display_name || currentUser?.immutable_id || "datalab user";
				const sampleCount = Array.isArray(sampleResponse?.samples) ? sampleResponse.samples.length : 0;
				this.message = `Hello ${name}. You can access ${sampleCount} sample(s).`;
			} catch (error) {
				this.message = `Error: ${error instanceof Error ? error.message : String(error)}`;
			}
		} }
	};
	var _hoisted_1 = { class: "datalab-tool-hello-in-app px-3 px-xl-5 py-3" };
	function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
		return (0, vue.openBlock)(), (0, vue.createElementBlock)("section", _hoisted_1, [_cache[0] || (_cache[0] = (0, vue.createElementVNode)("h1", { class: "h3" }, "Hello in-app", -1)), (0, vue.createElementVNode)("p", null, (0, vue.toDisplayString)($data.message), 1)]);
	}
	var ToolView_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
	//#endregion
	//#region src/main.js
	window.datalabToolSdk.register(ToolView_default);
	//#endregion
})(window.datalabToolSdk.runtime);
