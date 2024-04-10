<template>
    <VTooltip>
        <RouterLink as="button" to="/admin/settings/account" class="text-gray-500 dark:text-gray-400 focus:outline-none text-sm" type="button">
            <div class="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-200 hover:dark:bg-gray-700">
                <i class="fa-solid fa-md fa-user"></i>
            </div>
        </RouterLink>

        <template #popper>
            <span>{{ __("Account") }}</span>
        </template>
    </VTooltip>
</template>
