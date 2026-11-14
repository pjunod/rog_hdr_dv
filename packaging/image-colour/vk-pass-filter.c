/* SPDX-License-Identifier: MIT
 * Private test-only ELF interposition for the authenticated GTK loader path.
 * No replacement ICD, synthetic formats, renderer preference, or product API. */
#define _GNU_SOURCE
#include <vulkan/vulkan.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define MAX_FORMATS 256
static pthread_once_t once = PTHREAD_ONCE_INIT;
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static PFN_vkGetInstanceProcAddr next_gipa;
static PFN_vkGetDeviceProcAddr next_gdpa;
static PFN_vkGetPhysicalDeviceSurfaceFormatsKHR next_formats;
static PFN_vkCreateSwapchainKHR next_swapchain;
static int trace_fd = -1, filtering;

static void
record (const char *format, ...)
{
  char line[32768];
  va_list args;
  va_start (args, format);
  int n = vsnprintf (line, sizeof line, format, args);
  va_end (args);
  if (trace_fd < 0 || n < 0 || (size_t) n >= sizeof line)
    return;
  pthread_mutex_lock (&lock);
  ssize_t written = write (trace_fd, line, n);
  if (written != n)
    fprintf (stderr, "Vulkan fixture trace write failed; result is inconclusive\n");
  pthread_mutex_unlock (&lock);
}

static void
initialize (void)
{
  next_gipa = (PFN_vkGetInstanceProcAddr) dlsym (RTLD_NEXT, "vkGetInstanceProcAddr");
  next_gdpa = (PFN_vkGetDeviceProcAddr) dlsym (RTLD_NEXT, "vkGetDeviceProcAddr");
  next_formats = (PFN_vkGetPhysicalDeviceSurfaceFormatsKHR) dlsym (RTLD_NEXT, "vkGetPhysicalDeviceSurfaceFormatsKHR");
  next_swapchain = (PFN_vkCreateSwapchainKHR) dlsym (RTLD_NEXT, "vkCreateSwapchainKHR");
  const char *path = getenv ("GTK_COLOUR_FIXTURE_TRACE");
  if (path && path[0] == '/')
    trace_fd = open (path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
  if (trace_fd < 0)
    fprintf (stderr, "Vulkan fixture needs a fresh absolute trace path; no filtering applied\n");
  const char *mode = getenv ("GTK_COLOUR_FIXTURE_FILTER_PASS_THROUGH");
  filtering = trace_fd >= 0 && mode && strcmp (mode, "1") == 0;
  record ("{\"event\":\"init\",\"pid\":%ld,\"filter\":%s,\"pass_through_enum\":%d,\"exports_resolved\":%s}\n",
          (long) getpid (), filtering ? "true" : "false", VK_COLOR_SPACE_PASS_THROUGH_EXT,
          next_gipa && next_gdpa && next_formats && next_swapchain ? "true" : "false");
}

static void
formats_record (VkResult result, int count_only, const VkSurfaceFormatKHR *before,
                uint32_t n_before, const VkSurfaceFormatKHR *after, uint32_t n_after,
                uint32_t removed, int applied, uint32_t returned, uint32_t capacity)
{
  char line[32768];
  size_t used = snprintf (line, sizeof line,
    "{\"event\":\"formats\",\"result\":%d,\"count_only\":%s,\"applied\":%s,\"removed\":%u,\"returned_count\":%u,\"capacity\":%u,\"before\":[",
    result, count_only ? "true" : "false", applied ? "true" : "false", removed, returned, capacity);
  for (uint32_t i = 0; before && i < n_before && i < MAX_FORMATS; i++)
    used += snprintf (line + used, sizeof line - used, "%s[%d,%d]", i ? "," : "", before[i].format, before[i].colorSpace);
  used += snprintf (line + used, sizeof line - used, "],\"after\":[");
  for (uint32_t i = 0; after && i < n_after && i < MAX_FORMATS; i++)
    used += snprintf (line + used, sizeof line - used, "%s[%d,%d]", i ? "," : "", after[i].format, after[i].colorSpace);
  snprintf (line + used, sizeof line - used,
            "],\"n_before\":%u,\"n_after\":%u,\"truncated\":%s}\n",
            n_before, n_after, n_before > MAX_FORMATS || n_after > MAX_FORMATS ? "true" : "false");
  record ("%s", line);
}

static VkResult VKAPI_CALL
fixture_formats (VkPhysicalDevice physical, VkSurfaceKHR surface, uint32_t *count,
                 VkSurfaceFormatKHR *formats)
{
  pthread_once (&once, initialize);
  if (!next_formats)
    {
      record ("{\"event\":\"fixture_error\",\"reason\":\"missing_public_formats_export\"}\n");
      return VK_ERROR_INITIALIZATION_FAILED;
    }
  uint32_t capacity = count && formats ? *count : 0;
  if (!filtering || !count)
    {
      VkResult result = next_formats (physical, surface, count, formats);
      uint32_t n = count && (result == VK_SUCCESS || result == VK_INCOMPLETE) ? *count : 0;
      formats_record (result, formats == NULL, formats, n, formats, n, 0, 0, n, capacity);
      return result;
    }

  VkSurfaceFormatKHR actual[MAX_FORMATS], kept[MAX_FORMATS];
  uint32_t n_actual = 0;
  VkResult result = VK_INCOMPLETE;
  /* The ordinary bounded two-call enumeration handles genuine list changes. */
  for (unsigned attempt = 0; attempt < 3; attempt++)
    {
      result = next_formats (physical, surface, &n_actual, NULL);
      if (result != VK_SUCCESS)
        {
          record ("{\"event\":\"real_query_error\",\"result\":%d}\n", result);
          return result;
        }
      if (n_actual > MAX_FORMATS)
        break;
      result = next_formats (physical, surface, &n_actual, actual);
      if (result != VK_INCOMPLETE)
        break;
    }
  if (result != VK_SUCCESS || n_actual > MAX_FORMATS)
    {
      record ("{\"event\":\"fixture_error\",\"reason\":\"unstable_or_oversized_real_format_list\"}\n");
      return next_formats (physical, surface, count, formats); /* Unmodified; cannot qualify. */
    }
  uint32_t n_kept = 0;
  for (uint32_t i = 0; i < n_actual; i++)
    if (actual[i].colorSpace != VK_COLOR_SPACE_PASS_THROUGH_EXT)
      kept[n_kept++] = actual[i];
  if (n_kept == 0)
    {
      /* An empty advertised list is not an honest unsupported-PASS device.
       * Forward the real list instead; fixture_error makes this inconclusive. */
      record ("{\"event\":\"fixture_error\",\"reason\":\"no_real_non_pass_alternative\"}\n");
      return next_formats (physical, surface, count, formats);
    }
  uint32_t written = formats ? (*count < n_kept ? *count : n_kept) : n_kept;
  if (formats && written)
    memcpy (formats, kept, written * sizeof *formats);
  result = formats && written < n_kept ? VK_INCOMPLETE : VK_SUCCESS;
  *count = written;
  formats_record (result, formats == NULL, actual, n_actual, kept, n_kept, n_actual - n_kept, 1, written, capacity);
  return result;
}

static VkResult VKAPI_CALL
fixture_swapchain (VkDevice device, const VkSwapchainCreateInfoKHR *info,
                   const VkAllocationCallbacks *allocator, VkSwapchainKHR *swapchain)
{
  pthread_once (&once, initialize);
  record ("{\"event\":\"swapchain_attempt\",\"format\":%d,\"color_space\":%d}\n",
          info->imageFormat, info->imageColorSpace);
  if (!next_swapchain)
    {
      record ("{\"event\":\"fixture_error\",\"reason\":\"missing_public_swapchain_export\"}\n");
      return VK_ERROR_INITIALIZATION_FAILED;
    }
  VkResult result = next_swapchain (device, info, allocator, swapchain);
  record ("{\"event\":\"swapchain_result\",\"result\":%d}\n", result);
  return result;
}

static PFN_vkVoidFunction VKAPI_CALL fixture_gipa (VkInstance, const char *);
static PFN_vkVoidFunction VKAPI_CALL fixture_gdpa (VkDevice, const char *);

static PFN_vkVoidFunction
intercept (PFN_vkVoidFunction real, const char *name, const char *via)
{
  if (!real || !name)
    return real; /* Preserve the real entrypoint's NULL/scope semantics. */
  PFN_vkVoidFunction replacement = NULL;
  if (strcmp (name, "vkGetPhysicalDeviceSurfaceFormatsKHR") == 0)
    replacement = (PFN_vkVoidFunction) fixture_formats;
  else if (strcmp (name, "vkCreateSwapchainKHR") == 0)
    replacement = (PFN_vkVoidFunction) fixture_swapchain;
  else if (strcmp (name, "vkGetInstanceProcAddr") == 0)
    replacement = (PFN_vkVoidFunction) fixture_gipa;
  else if (strcmp (name, "vkGetDeviceProcAddr") == 0)
    replacement = (PFN_vkVoidFunction) fixture_gdpa;
  else if (strcmp (name, "vkGetPhysicalDeviceSurfaceFormats2KHR") == 0)
    record ("{\"event\":\"fixture_error\",\"reason\":\"uncovered_formats2_dispatch\"}\n");
  if (replacement)
    record ("{\"event\":\"dispatch_intercept\",\"via\":\"%s\",\"name\":\"%s\"}\n", via, name);
  return replacement ? replacement : real;
}

static PFN_vkVoidFunction VKAPI_CALL
fixture_gipa (VkInstance instance, const char *name)
{
  pthread_once (&once, initialize);
  return next_gipa ? intercept (next_gipa (instance, name), name, "GIPA") : NULL;
}

static PFN_vkVoidFunction VKAPI_CALL
fixture_gdpa (VkDevice device, const char *name)
{
  pthread_once (&once, initialize);
  return next_gdpa ? intercept (next_gdpa (device, name), name, "GDPA") : NULL;
}

VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL vkGetInstanceProcAddr (VkInstance instance, const char *name)
{ return fixture_gipa (instance, name); }
VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL vkGetDeviceProcAddr (VkDevice device, const char *name)
{ return fixture_gdpa (device, name); }
VKAPI_ATTR VkResult VKAPI_CALL vkGetPhysicalDeviceSurfaceFormatsKHR (VkPhysicalDevice physical, VkSurfaceKHR surface, uint32_t *count, VkSurfaceFormatKHR *formats)
{ return fixture_formats (physical, surface, count, formats); }
VKAPI_ATTR VkResult VKAPI_CALL vkCreateSwapchainKHR (VkDevice device, const VkSwapchainCreateInfoKHR *info, const VkAllocationCallbacks *allocator, VkSwapchainKHR *swapchain)
{ return fixture_swapchain (device, info, allocator, swapchain); }
