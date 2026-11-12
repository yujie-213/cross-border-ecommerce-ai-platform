<script setup lang="ts">withDefaults(defineProps<{ title?: string; tone?: string; alert?: boolean }>(), { tone: 'info' })</script>
<template><div class="notice" :class="tone" :role="alert ? 'alert' : 'status'"><div><strong v-if="title">{{ title }}</strong><slot /></div></div></template>
