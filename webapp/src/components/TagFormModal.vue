<template>
  <form class="modal-enclosure" data-testid="tag-form" @submit.prevent="submitForm">
    <Modal
      :model-value="modelValue"
      :disable-submit="!isFormValid"
      @update:model-value="$emit('update:modelValue', $event)"
    >
      <template #header>{{ isEditing ? "Edit tag" : "Create new tag" }}</template>

      <template #body>
        <div class="form-row">
          <div class="form-group col-md-12">
            <label for="tag-name">Name:</label>
            <input id="tag-name" v-model="name" type="text" class="form-control" required />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group col-md-12">
            <label for="tag-description">Description:</label>
            <textarea
              id="tag-description"
              v-model="description"
              class="form-control"
              rows="2"
            ></textarea>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group col-md-12">
            <label>Color:</label>
            <TagColorPicker v-model="color" :preview-label="name || 'preview'" />
          </div>
        </div>
        <div v-if="isAdmin" class="form-row">
          <div class="form-group col-md-12 mb-1">
            <div class="custom-control custom-checkbox">
              <input
                id="tag-global"
                v-model="isGlobal"
                type="checkbox"
                class="custom-control-input"
              />
              <label class="custom-control-label" for="tag-global">
                Global tag (visible to everyone)
              </label>
            </div>
            <small class="text-muted">
              A global tag has no owner; it cannot also be assigned creators or groups.
            </small>
          </div>
        </div>
        <template v-if="!isGlobal">
          <div class="form-row">
            <div class="form-group col-md-12">
              <label id="tagGroupsLabel">(Optional) Share with groups:</label>
              <GroupSelect v-model="shareWithGroups" aria-labelledby="tagGroupsLabel" multiple />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group col-md-12">
              <label id="tagCreatorsLabel">
                {{ isEditing ? "Creators:" : "(Optional) Additional creators:" }}
              </label>
              <UserSelect v-model="selectedCreators" aria-labelledby="tagCreatorsLabel" multiple />
            </div>
          </div>
        </template>
        <div v-if="errorMessage" class="form-error mt-2">{{ errorMessage }}</div>
      </template>
    </Modal>
  </form>
</template>

<script>
import { DialogService } from "@/services/DialogService";

import Modal from "@/components/Modal.vue";
import GroupSelect from "@/components/GroupSelect.vue";
import UserSelect from "@/components/UserSelect.vue";
import TagColorPicker from "@/components/TagColorPicker.vue";
import { createTag, updateTag, updateTagPermissions } from "@/server_fetch_utils.js";

export default {
  name: "TagFormModal",
  components: {
    Modal,
    GroupSelect,
    UserSelect,
    TagColorPicker,
  },
  props: {
    modelValue: Boolean,
    // When set, the modal edits this tag (a row from GET /tags); otherwise it creates a new one.
    tag: {
      type: Object,
      default: null,
    },
  },
  emits: ["update:modelValue", "tag-created", "tag-updated"],
  data() {
    return {
      name: "",
      description: "",
      color: null,
      // In create mode these are *additional* creators (the caller is always an owner). In edit
      // mode they are the *full* current creator set. `isGlobal` (admin only) makes the tag
      // owner-less (creator_ids: []), excluding groups/creators.
      shareWithGroups: [],
      selectedCreators: [],
      isGlobal: false,
      errorMessage: null,
      submitting: false,
    };
  },
  computed: {
    isEditing() {
      return Boolean(this.tag);
    },
    isAdmin() {
      return this.$store.state.currentUserRole === "admin";
    },
    isFormValid() {
      return !this.submitting && Boolean(this.name.trim());
    },
  },
  watch: {
    modelValue(isOpen) {
      // (Re)initialise the form whenever the modal opens, from the tag in edit mode.
      if (isOpen) {
        if (this.isEditing) {
          this.populateFromTag();
        } else {
          this.resetForm();
        }
      }
    },
  },
  methods: {
    populateFromTag() {
      this.name = this.tag.name || "";
      this.description = this.tag.description || "";
      this.color = this.tag.color || null;
      this.isGlobal = (this.tag.creator_ids || []).length === 0;
      // Copy the inlined creator/group objects (not references) so editing doesn't mutate store.
      this.selectedCreators = [...(this.tag.creators || [])];
      this.shareWithGroups = [...(this.tag.groups || [])];
      this.errorMessage = null;
    },
    resetForm() {
      this.name = "";
      this.description = "";
      this.color = null;
      this.shareWithGroups = [];
      this.selectedCreators = [];
      this.isGlobal = false;
      this.errorMessage = null;
    },
    buildCreatePayload() {
      const data = {
        name: this.name.trim(),
        description: this.description || null,
        color: this.color || null,
      };
      if (this.isGlobal) {
        data.creator_ids = [];
        return data;
      }
      // Additional creators are added alongside the caller; omitting creator_ids lets the
      // backend default the owner to the caller.
      if (this.selectedCreators.length) {
        const selfId = this.$store.state.currentUserID;
        const extraIds = this.selectedCreators.map((u) => u.immutable_id);
        data.creator_ids = selfId ? [selfId, ...extraIds.filter((id) => id !== selfId)] : extraIds;
      }
      if (this.shareWithGroups.length) {
        data.group_ids = this.shareWithGroups.map((g) => g.immutable_id || g._id);
      }
      return data;
    },
    metadataChanged() {
      return (
        this.name.trim() !== (this.tag.name || "") ||
        (this.description || null) !== (this.tag.description || null) ||
        (this.color || null) !== (this.tag.color || null)
      );
    },
    ownershipChanged() {
      const sortedIds = (arr) => arr.map(String).sort();
      const origCreators = sortedIds(this.tag.creator_ids || []);
      const origGroups = sortedIds(this.tag.group_ids || []);
      const newCreators = this.isGlobal
        ? []
        : sortedIds(this.selectedCreators.map((u) => u.immutable_id));
      const newGroups = this.isGlobal
        ? []
        : sortedIds(this.shareWithGroups.map((g) => g.immutable_id || g._id));
      return (
        JSON.stringify(origCreators) !== JSON.stringify(newCreators) ||
        JSON.stringify(origGroups) !== JSON.stringify(newGroups)
      );
    },
    async submitForm() {
      if (!this.isFormValid) {
        return;
      }
      this.errorMessage = null;
      this.submitting = true;
      try {
        if (this.isEditing) {
          await this.submitEdit();
          this.$emit("tag-updated");
        } else {
          await createTag(this.buildCreatePayload());
          this.$emit("tag-created");
        }
        this.$emit("update:modelValue", false);
      } catch (error) {
        const message = typeof error === "string" ? error : error?.message || String(error);
        // A name clash within a scope is a 409 the user can fix inline; surface it in the form.
        if (message && message.toLowerCase().includes("already exists")) {
          this.errorMessage = message;
        } else {
          DialogService.error({
            title: this.isEditing ? "Tag Update Failed" : "Tag Creation Failed",
            message: `Error ${this.isEditing ? "updating" : "creating"} tag: ${message}`,
          });
        }
      } finally {
        this.submitting = false;
      }
    },
    async submitEdit() {
      const tagId = this.tag.immutable_id;
      if (this.metadataChanged()) {
        await updateTag(tagId, {
          name: this.name.trim(),
          description: this.description || null,
          color: this.color || null,
        });
      }
      if (this.ownershipChanged()) {
        // Send the full new owner/group sets; [] clears a scope (e.g. global = creators []).
        const creators = this.isGlobal
          ? []
          : this.selectedCreators.map((u) => ({ immutable_id: u.immutable_id }));
        const groups = this.isGlobal
          ? []
          : this.shareWithGroups.map((g) => ({ immutable_id: g.immutable_id || g._id }));
        await updateTagPermissions(tagId, creators, groups);
      }
    },
  },
};
</script>

<style scoped>
.form-error {
  color: red;
}

:deep(.form-error a) {
  color: #820000;
  font-weight: 600;
}

.modal-enclosure :deep(.modal-content) {
  max-height: 90vh;
  overflow: auto;
  scroll-behavior: smooth;
}
</style>
