<template>
  <section class="datalab-tool-hello-in-app px-3 px-xl-5 py-3">
    <h1 class="h3">Hello in-app</h1>
    <p>{{ message }}</p>
  </section>
</template>

<script>
const sdk = window.datalabToolSdk;

export default {
  name: "HelloInAppTool",
  data() {
    return {
      message: "Loading...",
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
          sdk.api.get("/samples/"),
        ]);
        const name = currentUser?.display_name || currentUser?.immutable_id || "datalab user";
        const sampleCount = Array.isArray(sampleResponse?.samples)
          ? sampleResponse.samples.length
          : 0;
        this.message = `Hello ${name}. You can access ${sampleCount} sample(s).`;
      } catch (error) {
        this.message = `Error: ${error instanceof Error ? error.message : String(error)}`;
      }
    },
  },
};
</script>
