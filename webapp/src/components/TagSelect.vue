<template>
  <vSelect
    ref="selectComponent"
    v-model="value"
    :options="tagOptions"
    label="name"
    multiple
    taggable
    :push-tags="false"
    :filterable="false"
    :create-option="createOption"
    placeholder="type to search or create a tag..."
    v-bind="$attrs"
    @search="debouncedAsyncSearch"
  >
    <template #no-options="{ searching }">
      <span v-if="isSearchFetchError" class="search-error">
        Couldn't reach the server to search tags &mdash; you can still type to create a free-text
        tag.
      </span>
      <span v-else-if="searching">
        No matching tags &mdash; keep typing to create a free-text tag.
      </span>
      <span v-else class="empty-search"> Type to search or create a tag... </span>
    </template>
    <template #option="{ name, immutable_id, color, description }">
      <span
        class="tag-option"
        :title="description || (immutable_id ? 'Managed tag' : 'Free-text tag')"
      >
        <span v-if="color" class="color-swatch" :style="{ backgroundColor: color }"></span>
        <span>{{ name }}</span>
        <span v-if="!immutable_id" class="free-text-tag-hint"> (new free-text tag)</span>
      </span>
    </template>
    <template #selected-option="{ name, immutable_id, color, description }">
      <span v-if="color" class="color-swatch" :style="{ backgroundColor: color }"></span>
      <span
        :class="{ 'font-italic': !immutable_id }"
        :title="description || (immutable_id ? 'Managed tag' : 'Free-text tag')"
        >{{ name }}</span
      >
    </template>
  </vSelect>
</template>

<script>
import vSelect from "vue-select";
import { searchTags } from "@/server_fetch_utils.js";
import { debounceTime } from "@/resources.js";

export default {
  components: {
    vSelect,
  },
  props: {
    // Each entry is either a free-text string or a reference object
    // `{ type: "tags", immutable_id, name, color?, description? }`, matching the
    // backend `tags` field (color/description are display fields, re-resolved on read).
    modelValue: {
      type: Array,
      default: () => [],
    },
  },
  emits: ["update:modelValue"],
  data() {
    return {
      debounceTimeout: null,
      tags: [],
      // Cache of search results keyed by immutable_id, used to recover display-only
      // details (e.g. color) for tags whose stored reference is stripped to id+name.
      tagDetailsById: {},
      isSearchFetchError: false,
    };
  },
  computed: {
    // Map between the backend union form (strings | reference objects) and the
    // object form vue-select works with internally (always `{ name, ... }`).
    value: {
      get() {
        return (this.modelValue || []).map((tag) => {
          if (typeof tag === "string") {
            return { name: tag };
          }
          // Display fields come from the backend-resolved item tag, falling back to
          // the search cache (e.g. for a tag just picked, before a re-resolve).
          const cached = this.tagDetailsById[tag.immutable_id] || {};
          return {
            name: tag.name,
            immutable_id: tag.immutable_id,
            type: "tags",
            color: tag.color ?? cached.color ?? null,
            description: tag.description ?? cached.description ?? null,
          };
        });
      },
      set(newValue) {
        // Preserve display fields (color/description) on the stored reference so
        // they survive the edit<->display toggle without a re-fetch. They are
        // re-resolved on every read, so this is harmless denormalisation (like `name`).
        const mapped = (newValue || []).map((tag) => {
          if (!tag.immutable_id) {
            return tag.name;
          }
          const ref = { type: "tags", immutable_id: tag.immutable_id, name: tag.name };
          if (tag.color) {
            ref.color = tag.color;
          }
          if (tag.description) {
            ref.description = tag.description;
          }
          return ref;
        });
        this.$emit("update:modelValue", mapped);
      },
    },
    tagOptions() {
      // Hide tags that are already selected. Managed tags are matched by id and
      // free-text tags by name.
      const selectedIds = new Set(this.value.map((tag) => tag.immutable_id).filter((id) => id));
      const selectedFreeTextNames = new Set(
        this.value.filter((tag) => !tag.immutable_id).map((tag) => tag.name),
      );
      return this.tags.filter((tag) =>
        tag.immutable_id
          ? !selectedIds.has(tag.immutable_id)
          : !selectedFreeTextNames.has(tag.name),
      );
    },
  },
  beforeUnmount() {
    clearTimeout(this.debounceTimeout);
  },
  methods: {
    async debouncedAsyncSearch(query, loading) {
      loading(true);
      clearTimeout(this.debounceTimeout); // reset the timer
      // The backend rejects an empty query with a 400, so skip the request entirely
      // (e.g. when the user clears the input) rather than surfacing a false error.
      if (!query.trim()) {
        this.tags = [];
        this.isSearchFetchError = false;
        loading(false);
        return;
      }
      this.debounceTimeout = setTimeout(async () => {
        this.isSearchFetchError = false; // clear stale error from a previous search
        await searchTags(query, 100)
          .then((tags) => {
            this.tags = tags;
            tags.forEach((tag) => {
              if (tag.immutable_id) {
                this.tagDetailsById[tag.immutable_id] = tag;
              }
            });
          })
          .catch((error) => {
            console.error("Fetch error");
            console.error(error);
            this.tags = []; // don't show stale results alongside the error message
            this.isSearchFetchError = true;
          });
        loading(false);
      }, debounceTime);
    },
    createOption(newOption) {
      // A typed value with no match becomes a free-text (string) tag.
      return { name: typeof newOption === "string" ? newOption.trim() : newOption.name };
    },
  },
};
</script>

<style scoped>
.tag-option {
  /* Fill the option row so the description tooltip triggers anywhere on the line. */
  display: block;
}
.color-swatch {
  display: inline-block;
  width: 0.7em;
  height: 0.7em;
  border-radius: 50%;
  margin-right: 0.3em;
  vertical-align: middle;
  border: 1px solid rgba(0, 0, 0, 0.25);
}
.free-text-tag-hint {
  color: #888;
  font-style: italic;
  margin-left: 0.25rem;
}
/* Keep the hint legible on vue-select's blue highlighted row by following its text color. */
:deep(.vs__dropdown-option--highlight .free-text-tag-hint) {
  color: inherit;
}
.search-error {
  color: #b00020;
}
</style>
