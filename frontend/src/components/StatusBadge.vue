<script setup lang="ts">
import { label } from '../domain'
defineProps<{ value: string }>()
</script>
<template><span class="badge" :class="{ success: ['SUCCEEDED', 'AVAILABLE'].includes(value), danger: ['FAILED', 'BLOCKED'].includes(value), warning: ['PARTIAL', 'UNAVAILABLE', 'CANCELLED'].includes(value), info: ['QUEUED', 'RUNNING', 'RULES_ONLY'].includes(value) }">{{ label(value) }}</span></template>
