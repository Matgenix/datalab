<template>
  <section class="datalab-tool-hello-in-app hello-in-app-page px-3 px-xl-5 py-3">
    <h1 class="h3">Hello in-app</h1>
    <p v-if="isLoading" class="text-muted">Loading...</p>
    <p v-else-if="loadError" class="text-danger">Error: {{ loadError }}</p>
    <p v-else>Hello {{ displayName }}. You can access {{ sampleCount }} sample(s).</p>
  </section>
</template>

<script>
const sdk = window.DatalabToolSDK;

export default {
  name: "HelloInAppTool",
  data() {
    return {
      isLoading: true,
      loadError: null,
      displayName: "datalab user",
      sampleCount: 0,
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
        this.displayName = currentUser?.display_name || currentUser?.immutable_id || "datalab user";
        this.sampleCount = Array.isArray(sampleResponse?.samples)
          ? sampleResponse.samples.length
          : 0;
      } catch (error) {
        this.loadError = error instanceof Error ? error.message : String(error);
      } finally {
        this.isLoading = false;
      }
    },
  },
};
</script>
