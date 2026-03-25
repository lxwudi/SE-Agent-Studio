<template>
  <RouterView v-if="route.meta.noShell" />
  <AppShell v-else>
    <RouterView />
  </AppShell>
</template>

<script setup lang="ts">
import { RouterView, useRoute } from "vue-router";

import AppShell from "./layouts/AppShell.vue";


const route = useRoute();
</script>
