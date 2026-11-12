<script setup lang="ts">defineProps<{ title: string; note?: string }>()</script>
<template><section class="panel"><div class="panel-head"><h2>{{ title }}</h2><small v-if="note">{{ note }}</small><slot name="action" /></div><div class="panel-body"><slot /></div></section></template>
