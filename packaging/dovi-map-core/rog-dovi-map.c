/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* The qualification, target and mapping rules moved out of
 * packaging/gstreamer-gtk-dovi/mapper.c, stream.h and render-preconditions.h
 * (0.1.0+rogdv11) with their behaviour unchanged. Comments that start with
 * "GTK:" record where a rule came from. */
#define _GNU_SOURCE
#include "rog-dovi-map.h"
#include <dv_provider387.h>
#if !defined(DV_PROVIDER387_TARGET_V2_VERSION) || DV_PROVIDER387_TARGET_V2_VERSION != 2
#error "Dolby provider target API v2 headers are required"
#endif
/* Optional additive API: binaries remain loadable with the v1 runtime. */
#pragma weak dv_provider387_map_v2
#pragma weak dv_provider387_last_target_strategy
#include <libplacebo/vulkan.h>
#include <libplacebo/renderer.h>
#include <libplacebo/dispatch.h>
#include <libplacebo/cache.h>
#include <libplacebo/shaders/sampling.h>
#include <libplacebo/shaders/colorspace.h>
#include <libplacebo/shaders/custom.h>
#include <libplacebo/utils/libav.h>
#include <libavutil/imgutils.h>
#include <libavutil/pixdesc.h>
#include <libavutil/hwcontext.h>
#include <libavutil/hwcontext_drm.h>
#include <libavutil/dovi_meta.h>
#include <libavutil/mem.h>
#include <gbm.h>
#include <drm_fourcc.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <math.h>
#include <pthread.h>
#include <stdalign.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <unistd.h>
#include <vulkan/vulkan.h>

_Static_assert (DV_PROVIDER387_ABI == 1, "Unsupported provider ABI");

uint32_t rog_dovi_map_abi (void) { return ROG_DOVI_MAP_ABI; }

/* ---- Logging ---------------------------------------------------------- */
static pthread_mutex_t log_lock = PTHREAD_MUTEX_INITIALIZER;
static rog_dovi_log_fn log_fn;
static void *log_user;
static int log_max;
static pl_log placebo_log;

static enum pl_log_level placebo_level (int level)
{
  switch (level) {
    case ROG_DOVI_LOG_ERROR: return PL_LOG_ERR;
    case ROG_DOVI_LOG_WARN: return PL_LOG_WARN;
    case ROG_DOVI_LOG_INFO: return PL_LOG_INFO;
    case ROG_DOVI_LOG_DEBUG: return PL_LOG_DEBUG;
    case ROG_DOVI_LOG_TRACE: return PL_LOG_TRACE;
    default: return PL_LOG_NONE;
  }
}

static void emit (int level, const char *message)
{
  pthread_mutex_lock (&log_lock);
  rog_dovi_log_fn fn = log_fn;
  void *user = log_user;
  bool wanted = fn && level <= log_max;
  pthread_mutex_unlock (&log_lock);
  if (wanted) fn (user, level, message);
}

__attribute__((format (printf, 2, 3)))
static void logf_ (int level, const char *format, ...)
{
  pthread_mutex_lock (&log_lock);
  bool wanted = log_fn && level <= log_max;
  pthread_mutex_unlock (&log_lock);
  if (!wanted) return;
  char message[512];
  va_list args;
  va_start (args, format);
  vsnprintf (message, sizeof (message), format, args);
  va_end (args);
  emit (level, message);
}

static void placebo_cb (void *priv, enum pl_log_level level, const char *message)
{
  (void) priv;
  int ours = level <= PL_LOG_ERR ? ROG_DOVI_LOG_ERROR : level == PL_LOG_WARN ? ROG_DOVI_LOG_WARN :
      level == PL_LOG_INFO ? ROG_DOVI_LOG_INFO : level == PL_LOG_DEBUG ? ROG_DOVI_LOG_DEBUG :
      ROG_DOVI_LOG_TRACE;
  emit (ours, message);
}

/* One process-wide libplacebo log, created before the first device and never
 * destroyed: devices outlive any one mapper. Its own lock, not log_lock:
 * creating it already logs through placebo_cb. */
static pthread_mutex_t placebo_log_lock = PTHREAD_MUTEX_INITIALIZER;
static pl_log shared_log (void)
{
  pthread_mutex_lock (&placebo_log_lock);
  if (!placebo_log) {
    pthread_mutex_lock (&log_lock);
    enum pl_log_level level = log_fn ? placebo_level (log_max) : PL_LOG_NONE;
    pthread_mutex_unlock (&log_lock);
    placebo_log = pl_log_create (PL_API_VER, pl_log_params (.log_cb = placebo_cb, .log_level = level));
  }
  pl_log log = placebo_log;
  pthread_mutex_unlock (&placebo_log_lock);
  return log;
}

void rog_dovi_map_set_log (rog_dovi_log_fn fn, void *user, int max_level)
{
  pthread_mutex_lock (&placebo_log_lock);
  pthread_mutex_lock (&log_lock);
  log_fn = fn; log_user = user; log_max = fn ? max_level : 0;
  pthread_mutex_unlock (&log_lock);
  if (placebo_log) pl_log_level_update (placebo_log, fn ? placebo_level (max_level) : PL_LOG_NONE);
  pthread_mutex_unlock (&placebo_log_lock);
}

/* ---- Stream qualification (GTK: stream.h, render-preconditions.h) ------ */
uint32_t rog_dovi_map_stream_profile (const struct rog_dovi_stream_config *c, int fel_decoder)
{
  if (!c || c->version_major != 1 || c->version_minor != 0 || !c->rpu_present ||
      !c->bl_present || c->md_compression != AV_DOVI_COMPRESSION_NONE) return 0;
  if (c->el_present)
    return c->profile == 7 && c->bl_signal_compatibility_id == 6 && fel_decoder ? 7 : 0;
  if (c->profile == 5 && c->bl_signal_compatibility_id == 0) return 5;
  if (c->profile == 8 && c->bl_signal_compatibility_id == 1) return 8;
  return 0;
}

/* Called with the decoder-owned complete configuration, never an RPU profile
 * guess. Profile 5 IPT base samples have no ordinary HDR10 interpretation. */
int rog_dovi_map_profile5_has_no_base_fallback (const struct rog_dovi_stream_config *c)
{
  return c && c->version_major == 1 && c->version_minor == 0 &&
      c->profile == 5 && c->bl_signal_compatibility_id == 0 &&
      c->rpu_present && c->bl_present && !c->el_present &&
      c->md_compression == AV_DOVI_COMPRESSION_NONE;
}

int rog_dovi_map_same_config (const struct rog_dovi_stream_config *a,
    const struct rog_dovi_stream_config *b)
{
  return a && b && a->version_major == b->version_major &&
      a->version_minor == b->version_minor && a->profile == b->profile &&
      a->level == b->level && a->rpu_present == b->rpu_present &&
      a->el_present == b->el_present && a->bl_present == b->bl_present &&
      a->bl_signal_compatibility_id == b->bl_signal_compatibility_id &&
      a->md_compression == b->md_compression;
}

static bool profile5_destination_supported (const struct rog_dovi_stream_config *config,
    bool sdr, const struct rog_dovi_target *physical)
{
  const uint32_t witness = ROG_DOVI_TARGET_VALID | ROG_DOVI_TARGET_RENDER_READY | ROG_DOVI_TARGET_COMPOSED;
  return !rog_dovi_map_profile5_has_no_base_fallback (config) || sdr ||
      (physical && (physical->flags & witness) == witness);
}

int rog_dovi_map_profile5_destination_supported (const struct rog_dovi_stream_config *config,
    enum rog_dovi_destination destination, const struct rog_dovi_target *physical)
{
  return profile5_destination_supported (config,
      destination == ROG_DOVI_DESTINATION_STANDARD_SDR_SRGB, physical);
}

/* ---- Vulkan devices (GTK: mapper.c acquire/release_vulkan) ------------- */
/* One Vulkan device and shader cache per render node per process. Creating
 * an instance and a device costs hundreds of milliseconds; a consumer that
 * created its own on its first visible picture (the browser compositor) held
 * presentation that long after playback started, and the decoder dropped the
 * opening pictures as late. The Vulkan pl_gpu is thread-safe; renderers,
 * dispatches, textures and the provider stay per mapper. The cache lets later
 * mappers reuse compiled passes. A GPU that is not thread-safe gets a device
 * of the mapper's own instead. Node 0 is libplacebo's default selection. */
struct device {
  uint64_t node;
  pl_vulkan vk;
  pl_cache cache;
  unsigned users;
  bool keep;                /* a ROG_DOVI_MAPPER_KEEP_DEVICE mapper acquired it */
  struct device *next;
};
static pthread_mutex_t shared_gpu_lock = PTHREAD_MUTEX_INITIALIZER;
static struct device *shared_devices;

static void log_device (pl_vulkan vk)
{
  PFN_vkGetPhysicalDeviceProperties get_properties =
      (PFN_vkGetPhysicalDeviceProperties) vk->get_proc_addr (vk->instance, "vkGetPhysicalDeviceProperties");
  if (get_properties) {
    VkPhysicalDeviceProperties properties;
    get_properties (vk->phys_device, &properties);
    logf_ (ROG_DOVI_LOG_INFO, "native mapper Vulkan device vendor=%04x device=%04x type=%u name=%s",
        properties.vendorID, properties.deviceID, properties.deviceType, properties.deviceName);
  }
}

/* The Vulkan device whose DRM render node is node, by its UUID. The
 * enumeration instance is created once and never destroyed. Destroying it
 * dlcloses every ICD it loaded, including the NVIDIA one when the picture
 * is rendered on Intel; a process that later exits then crashed in the
 * unloaded NVIDIA libraries (measured on the lab host, 7 of 8 runs). Holding
 * the instance keeps the loaded ICDs for the process lifetime. */
static pthread_mutex_t enumeration_lock = PTHREAD_MUTEX_INITIALIZER;
static VkInstance enumeration_instance;
static bool uuid_for_node (uint64_t node, uint8_t uuid[VK_UUID_SIZE])
{
  pthread_mutex_lock (&enumeration_lock);
  if (!enumeration_instance) {
    VkApplicationInfo app = {.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO, .apiVersion = VK_API_VERSION_1_1};
    if (vkCreateInstance (&(VkInstanceCreateInfo) {.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
        .pApplicationInfo = &app}, NULL, &enumeration_instance) != VK_SUCCESS)
      enumeration_instance = VK_NULL_HANDLE;
  }
  VkInstance inst = enumeration_instance;
  pthread_mutex_unlock (&enumeration_lock);
  if (!inst) return false;
  uint32_t n = 0;
  bool found = false;
  vkEnumeratePhysicalDevices (inst, &n, NULL);
  VkPhysicalDevice phys[16];
  if (n > 16) n = 16;
  vkEnumeratePhysicalDevices (inst, &n, phys);
  for (uint32_t i = 0; i < n && !found; i++) {
    uint32_t ne = 0;
    vkEnumerateDeviceExtensionProperties (phys[i], NULL, &ne, NULL);
    VkExtensionProperties *ext = calloc (ne ? ne : 1, sizeof (*ext));
    bool has_drm = false;
    if (ext && vkEnumerateDeviceExtensionProperties (phys[i], NULL, &ne, ext) == VK_SUCCESS)
      for (uint32_t e = 0; e < ne; e++)
        has_drm |= !strcmp (ext[e].extensionName, VK_EXT_PHYSICAL_DEVICE_DRM_EXTENSION_NAME);
    free (ext);
    if (!has_drm) continue;
    VkPhysicalDeviceIDProperties id = {.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ID_PROPERTIES};
    VkPhysicalDeviceDrmPropertiesEXT drm = {.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRM_PROPERTIES_EXT, .pNext = &id};
    VkPhysicalDeviceProperties2 props = {.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2, .pNext = &drm};
    vkGetPhysicalDeviceProperties2 (phys[i], &props);
    if (drm.hasRender && (uint64_t) makedev (drm.renderMajor, drm.renderMinor) == node) {
      memcpy (uuid, id.deviceUUID, VK_UUID_SIZE);
      found = true;
    }
  }
  return found;
}

static pl_vulkan create_vulkan (uint64_t node)
{
  struct pl_vulkan_params params = pl_vulkan_default_params;
  params.allow_software = true;
  if (node) {
    uint8_t uuid[VK_UUID_SIZE];
    if (!uuid_for_node (node, uuid)) {
      logf_ (ROG_DOVI_LOG_ERROR, "no Vulkan device has render node %u:%u",
          major ((dev_t) node), minor ((dev_t) node));
      return NULL;
    }
    memcpy (params.device_uuid, uuid, sizeof (uuid));
  }
  return pl_vulkan_create (shared_log (), &params);
}

static pl_vulkan acquire_vulkan (uint64_t node, bool keep, bool *shared)
{
  pthread_mutex_lock (&shared_gpu_lock);
  struct device **link = &shared_devices;
  while (*link && (*link)->node != node) link = &(*link)->next;
  if (!*link) {
    pl_vulkan vk = create_vulkan (node);
    if (vk) {
      log_device (vk);
      struct device *d = calloc (1, sizeof (*d));
      if (!d) {
        pl_vulkan_destroy (&vk);
      } else {
        d->node = node;
        d->vk = vk;
        if (vk->gpu->limits.thread_safe) {
          d->cache = pl_cache_create (pl_cache_params (.log = shared_log (), .max_total_size = 64 << 20));
          pl_gpu_set_cache (vk->gpu, d->cache);
        }
        *link = d;
      }
    }
  }
  struct device *d = *link;
  pl_vulkan vk = d ? d->vk : NULL;
  *shared = vk && vk->gpu->limits.thread_safe;
  if (*shared) {
    d->users++;
    d->keep |= keep;
  } else if (d) {
    /* Never shared: the creating mapper keeps it as its own. */
    *link = d->next;
    free (d);
  }
  pthread_mutex_unlock (&shared_gpu_lock);
  return vk;
}

/* Destroying a Vulkan instance lets the loader unload the driver's ICD. The
 * NVIDIA ICD is its GL vendor library, and unloading it releases the calling
 * thread's current EGL context (eglReleaseThread). The last mapper is freed on
 * whichever thread drops the pipeline: WebKit's main thread on a source change,
 * whose Skia context then silently stopped being current, so its next tile
 * textures were never created and the tile painter crashed. Devices are
 * therefore destroyed on a thread of this library; destroys run one at a time
 * (a new device may be created meanwhile). At exit, pending destroys finish
 * before any library is finalized. */
struct release_job { pl_vulkan vk; pl_cache cache; struct release_job *next; };
static pthread_mutex_t vulkan_release_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t vulkan_release_cond = PTHREAD_COND_INITIALIZER;
static struct release_job *release_head, *release_tail;
static pthread_t vulkan_release_thread;
static bool vulkan_release_started, vulkan_release_stopping, vulkan_release_drained;

static void destroy_vulkan (struct release_job *job)
{
  pl_vulkan_destroy (&job->vk);
  pl_cache_destroy (&job->cache);
  free (job);
}

static void *release_worker (void *unused)
{
  (void) unused;
  for (;;) {
    pthread_mutex_lock (&vulkan_release_lock);
    while (!release_head && !vulkan_release_stopping)
      pthread_cond_wait (&vulkan_release_cond, &vulkan_release_lock);
    struct release_job *job = release_head;
    if (job) {
      release_head = job->next;
      if (!release_head) release_tail = NULL;
    }
    pthread_mutex_unlock (&vulkan_release_lock);
    if (!job) return NULL; /* stopping and drained */
    destroy_vulkan (job);
  }
}

static void drain_vulkan_releases (void)
{
  pthread_mutex_lock (&vulkan_release_lock);
  bool started = vulkan_release_started;
  vulkan_release_stopping = true;
  vulkan_release_drained = true;
  pthread_cond_signal (&vulkan_release_cond);
  pthread_mutex_unlock (&vulkan_release_lock);
  /* Queued destroys finish first, as with the GTK element's thread pool. */
  if (started) pthread_join (vulkan_release_thread, NULL);
}

static void destroy_vulkan_off_thread (pl_vulkan vk, pl_cache cache)
{
  struct release_job *job = calloc (1, sizeof (*job));
  if (!job) {
    /* Out of memory: there is no other place to run it. */
    struct release_job stack = {vk, cache, NULL};
    pl_vulkan_destroy (&stack.vk);
    pl_cache_destroy (&stack.cache);
    return;
  }
  job->vk = vk;
  job->cache = cache;
  pthread_mutex_lock (&vulkan_release_lock);
  if (!vulkan_release_started && !vulkan_release_drained) {
    /* atexit handlers run before library finalizers (and at dlclose). */
    if (!pthread_create (&vulkan_release_thread, NULL, release_worker, NULL)) {
      vulkan_release_started = true;
      atexit (drain_vulkan_releases);
    }
  }
  if (vulkan_release_started && !vulkan_release_stopping) {
    if (release_tail) release_tail->next = job; else release_head = job;
    release_tail = job;
    pthread_cond_signal (&vulkan_release_cond);
    job = NULL;
  }
  pthread_mutex_unlock (&vulkan_release_lock);
  /* Only after the exit drain: the process is finishing on this thread. */
  if (job) destroy_vulkan (job);
}

/* The last mapper out destroys the device: a web process without video should
 * not keep one. A new pipeline's own mapper creates the next device while it
 * prerolls, before the clock runs. */
static void release_vulkan (pl_vulkan *vk, bool shared, bool keep)
{
  if (!*vk) return;
  if (!shared) {
    /* A kept device of the mapper's own is deliberately never destroyed. */
    if (!keep) destroy_vulkan_off_thread (*vk, NULL);
    *vk = NULL;
    return;
  }
  pthread_mutex_lock (&shared_gpu_lock);
  struct device **link = &shared_devices;
  while (*link && (*link)->vk != *vk) link = &(*link)->next;
  struct device *d = *link;
  if (d && d->users && !--d->users && !d->keep) {
    *link = d->next;
    destroy_vulkan_off_thread (d->vk, d->cache);
    free (d);
  }
  pthread_mutex_unlock (&shared_gpu_lock);
  *vk = NULL;
}

/* ---- Mapper ----------------------------------------------------------- */
struct rog_dovi_mapper {
  uint64_t input_node, output_node;
  bool keep_device;
  pl_vulkan vk;
  bool shared_vk;
  pl_renderer renderer;
  pl_dispatch dispatch;
  pl_tex transport;
  struct pl_color_space physical;
  float transport_gain;
  struct dv_provider387 *provider;
  pl_tex source[4], enhancement[4], output[4], sdr_intermediate[4], sdr_output[4];
  bool has_destination, last_sdr_destination;
  bool requires_fel;
  int mapped;
  uint32_t target_strategy_witness;
  uint32_t declined;
  int failure;
  AVBufferRef *drm_device, *drm_frames;
  struct gbm_device *gbm;
  int gbm_fd;
};

static void decline (rog_dovi_mapper *s, uint32_t bit) { s->declined |= bit; }

static int fail (rog_dovi_mapper *s, const char **error, int kind, const char *what)
{
  /* The first reason stands: a later generic exit never replaces it. */
  if (s && s->failure == ROG_DOVI_FAILURE_NONE) s->failure = kind;
  if (error && !*error) *error = what;
  return -1;
}

const char *rog_dovi_map_decline_reason (uint32_t bit)
{
  switch (bit) {
    case ROG_DOVI_DECLINE_NOT_ELIGIBLE: return "picture or destination not eligible; ordinary conversion";
    case ROG_DOVI_DECLINE_UNQUALIFIED: return "per-picture metadata/geometry/enhancement unqualified; baseline conversion";
    case ROG_DOVI_DECLINE_TARGET: return "invalid/non-HDR surface target; baseline conversion";
    case ROG_DOVI_DECLINE_PROVIDER: return "provider declined; ordinary baseline re-encoding";
    case ROG_DOVI_DECLINE_TRANSPORT: return "actual HDR render declaration/transport unqualified";
    case ROG_DOVI_DECLINE_ENHANCEMENT: return "matched enhancement planes unavailable";
    case ROG_DOVI_DECLINE_COMPOSITION: return "renderer did not reconstruct the Profile 7 master";
    case ROG_DOVI_DECLINE_OUTPUT_IMPORT: return "output node cannot import the mapped picture";
    default: return NULL;
  }
}

uint32_t rog_dovi_map_last_decline (const rog_dovi_mapper *s) { return s ? s->declined : 0; }
int rog_dovi_map_last_failure (const rog_dovi_mapper *s) { return s ? s->failure : ROG_DOVI_FAILURE_INTERNAL; }

static int provider_map (void *priv, pl_gpu gpu, const uint8_t *rpu, size_t size,
    bool composed, const struct pl_color_space *target, pl_tex master,
    pl_tex *mapped, struct pl_color_space *color)
{
  rog_dovi_mapper *s = priv;
  if (s->requires_fel && !composed) {
    decline (s, ROG_DOVI_DECLINE_COMPOSITION);
    return s->mapped = 0;
  }
  uint32_t strategy = 4; /* v1 runtime: complete named mapping */
  if (dv_provider387_map_v2) {
    s->mapped = dv_provider387_map_v2 (s->provider, gpu, rpu, size, composed,
        &s->physical, master, mapped, color, NULL);
    if (dv_provider387_last_target_strategy)
      strategy = dv_provider387_last_target_strategy (s->provider);
  } else {
    s->mapped = dv_provider387_map (s->provider, gpu, rpu, size, composed,
        &s->physical, master, mapped, color);
  }
  if (s->mapped == 1 && s->target_strategy_witness != strategy + 1) {
    static const char *const names[] = { "named", "raw-xy-neutral-cm4",
      "named-creative-fallback", "named-invalid-xy-fallback", "named-v1-runtime" };
    logf_ (ROG_DOVI_LOG_INFO, "Dolby target strategy=%s",
        strategy < sizeof (names) / sizeof (names[0]) ? names[strategy] : "unknown");
    s->target_strategy_witness = strategy + 1;
  }
  if (s->mapped != 1) return s->mapped;
  if (s->requires_fel)
    logf_ (ROG_DOVI_LOG_TRACE, "Profile 7 provider accepted composed %dx%d master",
        master->params.w, master->params.h);
  if (s->transport_gain != 1.0f) {
    pl_fmt fmt = pl_find_fmt (gpu, PL_FMT_FLOAT, 4, 32, 0,
        PL_FMT_CAP_RENDERABLE | PL_FMT_CAP_SAMPLEABLE | PL_FMT_CAP_HOST_READABLE);
    if (!fmt || !pl_tex_recreate (gpu, &s->transport, pl_tex_params (
        .w = (*mapped)->params.w, .h = (*mapped)->params.h, .format = fmt,
        .sampleable = true, .renderable = true, .host_readable = true,
        .storable = fmt->caps & PL_FMT_CAP_STORABLE))) return s->mapped = -1;
    pl_shader sh = pl_dispatch_begin (s->dispatch);
    if (!pl_shader_sample_direct (sh, pl_sample_src (.tex = *mapped))) {
      pl_dispatch_abort (s->dispatch, &sh); return s->mapped = -1;
    }
    const struct pl_color_space pq = {.primaries = PL_COLOR_PRIM_BT_2020, .transfer = PL_COLOR_TRC_PQ};
    pl_shader_linearize (sh, &pq);
    struct pl_shader_var gain = {.var = pl_var_float ("dv_physical_transport_gain"),
        .data = &s->transport_gain, .dynamic = true};
    if (!pl_shader_custom (sh, &(struct pl_custom_shader) {
        .description = "physical DV to GTK PQ reference transport",
        .body = "color.rgb *= dv_physical_transport_gain;",
        .input = PL_SHADER_SIG_COLOR, .output = PL_SHADER_SIG_COLOR,
        .variables = &gain, .num_variables = 1})) {
      pl_dispatch_abort (s->dispatch, &sh); return s->mapped = -1;
    }
    pl_shader_delinearize (sh, &pq);
    if (!pl_dispatch_finish (s->dispatch, pl_dispatch_params (.shader = &sh, .target = s->transport)))
      return s->mapped = -1;
    *mapped = s->transport;
  }
  *color = *target;
  return s->mapped;
}

rog_dovi_mapper *rog_dovi_mapper_new (const struct rog_dovi_mapper_params *params)
{
  if (params && (params->struct_size < sizeof (*params) ||
      (params->flags & ~ROG_DOVI_MAPPER_KEEP_DEVICE))) return NULL;
  rog_dovi_mapper *s = calloc (1, sizeof (*s));
  if (!s) return NULL;
  if (params) {
    s->input_node = params->input_node; s->output_node = params->output_node;
    s->keep_device = params->flags & ROG_DOVI_MAPPER_KEEP_DEVICE;
  }
  s->gbm_fd = -1;
  return s;
}

void rog_dovi_mapper_free (rog_dovi_mapper *s)
{
  if (!s) return;
  if (s->vk) {
    dv_provider387_destroy (&s->provider);
    pl_renderer_destroy (&s->renderer);
    pl_dispatch_destroy (&s->dispatch);
    pl_tex_destroy (s->vk->gpu, &s->transport);
    for (unsigned i = 0; i < 4; i++) {
      pl_tex_destroy (s->vk->gpu, &s->source[i]);
      pl_tex_destroy (s->vk->gpu, &s->enhancement[i]);
      pl_tex_destroy (s->vk->gpu, &s->output[i]);
      pl_tex_destroy (s->vk->gpu, &s->sdr_intermediate[i]);
      pl_tex_destroy (s->vk->gpu, &s->sdr_output[i]);
    }
    release_vulkan (&s->vk, s->shared_vk, s->keep_device);
  }
  av_buffer_unref (&s->drm_frames);
  av_buffer_unref (&s->drm_device);
  if (s->gbm) gbm_device_destroy (s->gbm);
  if (s->gbm_fd >= 0) close (s->gbm_fd);
  free (s);
}

void rog_dovi_mapper_reset (rog_dovi_mapper *s)
{
  if (s && s->provider) dv_provider387_reset (s->provider);
}

static uint64_t render_node (const rog_dovi_mapper *s)
{
  return s->input_node ? s->input_node : s->output_node;
}

static bool ensure_device (rog_dovi_mapper *s)
{
  if (s->vk) return s->renderer && s->dispatch;
  s->vk = acquire_vulkan (render_node (s), s->keep_device, &s->shared_vk);
  if (!s->vk) return false;
  s->dispatch = pl_dispatch_create (shared_log (), s->vk->gpu);
  s->renderer = pl_renderer_create (shared_log (), s->vk->gpu);
  if (!s->dispatch || !s->renderer) {
    /* Retry from scratch next time instead of holding a device unusable here. */
    pl_renderer_destroy (&s->renderer);
    pl_dispatch_destroy (&s->dispatch);
    release_vulkan (&s->vk, s->shared_vk, s->keep_device);
    return false;
  }
  logf_ (ROG_DOVI_LOG_INFO, "native mapper %p uses %s Vulkan device", (void *) s,
      s->shared_vk ? "the process-shared" : "its own");
  return true;
}

uint32_t rog_dovi_map_profiles (const struct rog_dovi_mapper_params *params)
{
  if (dv_provider387_abi () != DV_PROVIDER387_ABI) return 0;
  rog_dovi_mapper *s = rog_dovi_mapper_new (params);
  if (!s) return 0;
  uint32_t mask = 0;
  if (ensure_device (s)) {
    s->provider = dv_provider387_create (s->vk->gpu, shared_log ());
    if (s->provider) mask = (1u << 5) | (1u << 7) | (1u << 8);
  }
  rog_dovi_mapper_free (s);
  return mask;
}

/* ---- Record validation ------------------------------------------------ */
static bool range_valid (size_t offset, size_t length, size_t size, size_t alignment)
{
  return offset >= sizeof (AVDOVIMetadata) && offset % alignment == 0 &&
      offset <= size && length <= size - offset;
}

/* AVDOVIMetadata is one allocation addressed by offsets; a blob that crossed
 * a process boundary is used only after every part lies inside it. */
static bool metadata_valid (const void *data, size_t size)
{
  if (!data || size < sizeof (AVDOVIMetadata) ||
      (uintptr_t) data % alignof (AVDOVIMetadata)) return false;
  const AVDOVIMetadata *m = data;
  if (!range_valid (m->header_offset, sizeof (AVDOVIRpuDataHeader), size, alignof (AVDOVIRpuDataHeader)) ||
      !range_valid (m->mapping_offset, sizeof (AVDOVIDataMapping), size, alignof (AVDOVIDataMapping)) ||
      !range_valid (m->color_offset, sizeof (AVDOVIColorMetadata), size, alignof (AVDOVIColorMetadata)) ||
      m->num_ext_blocks < 0 || m->num_ext_blocks > AV_DOVI_MAX_EXT_BLOCKS)
    return false;
  if (m->num_ext_blocks) {
    if (m->ext_block_size < sizeof (AVDOVIDmData) || m->ext_block_size % alignof (AVDOVIDmData) ||
        m->ext_block_size > SIZE_MAX / (size_t) m->num_ext_blocks ||
        !range_valid (m->ext_block_offset, m->ext_block_size * (size_t) m->num_ext_blocks,
            size, alignof (AVDOVIDmData)))
      return false;
  }
  return true;
}

static void config_from_record (const struct rog_dovi_picture *p,
    const struct rog_dovi_stream_config **config)
{
  *config = p && p->has_config ? &p->config : NULL;
}

static const AVDOVIMetadata *record_metadata (const struct rog_dovi_picture *p)
{
  if (!p || AV_VERSION_MAJOR (p->libavutil_version) != AV_VERSION_MAJOR (avutil_version ()) ||
      AV_VERSION_MAJOR (avutil_version ()) != LIBAVUTIL_VERSION_MAJOR ||
      !metadata_valid (p->metadata, p->metadata_size)) return NULL;
  return p->metadata;
}

/* ---- Formats ---------------------------------------------------------- */
static enum AVPixelFormat av_format (uint32_t f)
{
  switch (f) {
    case ROG_DOVI_FORMAT_RGBA: return AV_PIX_FMT_RGBA;
    case ROG_DOVI_FORMAT_BGRA: return AV_PIX_FMT_BGRA;
    case ROG_DOVI_FORMAT_RGB24: return AV_PIX_FMT_RGB24;
    case ROG_DOVI_FORMAT_BGR24: return AV_PIX_FMT_BGR24;
    case ROG_DOVI_FORMAT_RGB0: return AV_PIX_FMT_RGB0;
    case ROG_DOVI_FORMAT_BGR0: return AV_PIX_FMT_BGR0;
    case ROG_DOVI_FORMAT_RGBA64LE: return AV_PIX_FMT_RGBA64LE;
    case ROG_DOVI_FORMAT_NV12: return AV_PIX_FMT_NV12;
    case ROG_DOVI_FORMAT_P010LE: return AV_PIX_FMT_P010LE;
    case ROG_DOVI_FORMAT_YUV420P: return AV_PIX_FMT_YUV420P;
    case ROG_DOVI_FORMAT_YUV420P10LE: return AV_PIX_FMT_YUV420P10LE;
    default: return AV_PIX_FMT_NONE;
  }
}

/* GTK: GST_VIDEO_INFO_COMP_DEPTH (info, 0) of the native YUV inputs. */
static unsigned luma_depth (enum AVPixelFormat f)
{
  return f == AV_PIX_FMT_P010LE || f == AV_PIX_FMT_YUV420P10LE ? 10 : 8;
}

static bool download_row_pitch_ok (int stride, size_t texel_align, size_t row_bytes)
{
  /* libplacebo's transfer API consumes an unsigned, texel-aligned row pitch. */
  return stride > 0 && (size_t) stride >= row_bytes && texel_align &&
      (size_t) stride % texel_align == 0;
}

static bool direct_output_layout (int32_t stride, uint32_t width, size_t pixel_stride,
    const struct pl_frame *destination)
{
  if (destination->num_planes != 1) return false;
  pl_tex tex = destination->planes[0].texture;
  return tex && tex->params.format &&
      download_row_pitch_ok (stride, tex->params.format->texel_align, (size_t) width * pixel_stride);
}

/* ---- DMABuf input and output ------------------------------------------ */
static AVBufferRef *drm_frames (rog_dovi_mapper *s, enum AVPixelFormat sw, int w, int h)
{
  if (s->drm_frames) {
    const AVHWFramesContext *fc = (const AVHWFramesContext *) s->drm_frames->data;
    if (fc->sw_format == sw && fc->width == w && fc->height == h) return s->drm_frames;
    av_buffer_unref (&s->drm_frames);
  }
  if (!s->drm_device) {
    s->drm_device = av_hwdevice_ctx_alloc (AV_HWDEVICE_TYPE_DRM);
    if (!s->drm_device) return NULL;
    AVDRMDeviceContext *drm = ((AVHWDeviceContext *) s->drm_device->data)->hwctx;
    drm->fd = -1; /* descriptors only; the core never opens the device here */
    if (av_hwdevice_ctx_init (s->drm_device) < 0) { av_buffer_unref (&s->drm_device); return NULL; }
  }
  AVBufferRef *ref = av_hwframe_ctx_alloc (s->drm_device);
  if (!ref) return NULL;
  AVHWFramesContext *fc = (AVHWFramesContext *) ref->data;
  fc->format = AV_PIX_FMT_DRM_PRIME;
  fc->sw_format = sw;
  fc->width = w;
  fc->height = h;
  if (av_hwframe_ctx_init (ref) < 0) { av_buffer_unref (&ref); return NULL; }
  return s->drm_frames = ref;
}

/* The DMABuf picture as a DRM-PRIME AVFrame with one single-plane layer per
 * plane, the layout VA-API exports, so pl_map_avframe_ex imports it. */
static AVFrame *dmabuf_avframe (rog_dovi_mapper *s, const struct rog_dovi_dmabuf *in)
{
  bool p010 = in->drm_fourcc == DRM_FORMAT_P010;
  AVBufferRef *frames = drm_frames (s, p010 ? AV_PIX_FMT_P010LE : AV_PIX_FMT_NV12,
      (int) in->width, (int) in->height);
  AVDRMFrameDescriptor *desc = av_mallocz (sizeof (*desc));
  AVFrame *frame = av_frame_alloc ();
  if (!frames || !desc || !frame) goto error;
  frame->buf[0] = av_buffer_create ((uint8_t *) desc, sizeof (*desc), av_buffer_default_free, NULL, 0);
  if (!frame->buf[0]) goto error;
  AVDRMFrameDescriptor *d = desc;
  desc = NULL;
  const uint32_t layer_format[2] = {
    p010 ? DRM_FORMAT_R16 : DRM_FORMAT_R8, p010 ? DRM_FORMAT_GR1616 : DRM_FORMAT_GR88 };
  d->nb_layers = 2;
  for (unsigned i = 0; i < 2; i++) {
    int object = -1;
    for (int o = 0; o < d->nb_objects; o++) if (d->objects[o].fd == in->planes[i].fd) object = o;
    if (object < 0) {
      off_t end = lseek (in->planes[i].fd, 0, SEEK_END);
      if (end <= 0) goto error;
      object = d->nb_objects++;
      d->objects[object] = (AVDRMObjectDescriptor) {
        .fd = in->planes[i].fd, .size = (size_t) end, .format_modifier = in->modifier };
    }
    d->layers[i] = (AVDRMLayerDescriptor) {.format = layer_format[i], .nb_planes = 1,
      .planes = {{.object_index = object, .offset = in->planes[i].offset, .pitch = in->planes[i].pitch}}};
  }
  frame->data[0] = (uint8_t *) d;
  frame->format = AV_PIX_FMT_DRM_PRIME;
  frame->width = (int) in->width;
  frame->height = (int) in->height;
  frame->hw_frames_ctx = av_buffer_ref (frames);
  if (!frame->hw_frames_ctx) goto error;
  frame->color_range = in->color_range;
  frame->colorspace = in->colorspace;
  frame->color_primaries = in->color_primaries;
  frame->color_trc = in->color_trc;
  frame->chroma_location = in->chroma_location;
  return frame;
error:
  av_free (desc);
  av_frame_free (&frame);
  return NULL;
}

static bool node_path (uint64_t node, char *path, size_t size)
{
  DIR *dir = opendir ("/dev/dri");
  if (!dir) return false;
  bool found = false;
  for (struct dirent *e; !found && (e = readdir (dir));) {
    if (strncmp (e->d_name, "renderD", 7)) continue;
    snprintf (path, size, "/dev/dri/%s", e->d_name);
    struct stat st;
    found = !stat (path, &st) && S_ISCHR (st.st_mode) && (uint64_t) st.st_rdev == node;
  }
  closedir (dir);
  return found;
}

static bool list_has (const uint64_t *list, uint32_t n, uint64_t value)
{
  for (uint32_t i = 0; i < n; i++) if (list[i] == value) return true;
  return false;
}

/* Allocate the output on the output node and import it as a render target.
 * Returns the texture; *fd is the caller's fd for it. 0 with *declined when
 * no modifier both sides can use exists. */
static pl_tex allocate_output (rog_dovi_mapper *s, struct rog_dovi_output *out,
    int *fd, bool *declined)
{
  *fd = -1;
  *declined = false;
  pl_gpu gpu = s->vk->gpu;
  pl_fmt fmt = pl_find_fourcc (gpu, out->drm_fourcc);
  if (!fmt || !(fmt->caps & PL_FMT_CAP_RENDERABLE) || !(gpu->import_caps.tex & PL_HANDLE_DMA_BUF) ||
      !out->modifiers || !out->num_modifiers) return NULL;
  if (!s->gbm) {
    char path[288];
    if (!s->output_node || !node_path (s->output_node, path, sizeof (path))) return NULL;
    s->gbm_fd = open (path, O_RDWR | O_CLOEXEC);
    if (s->gbm_fd < 0) return NULL;
    s->gbm = gbm_create_device (s->gbm_fd);
    if (!s->gbm) return NULL;
  }
  uint64_t chosen[64];
  uint32_t n = 0;
  if (render_node (s) == s->output_node) {
    for (uint32_t i = 0; i < out->num_modifiers && n < 64; i++)
      if (pl_fmt_has_modifier (fmt, out->modifiers[i])) chosen[n++] = out->modifiers[i];
  } else if (list_has (out->modifiers, out->num_modifiers, DRM_FORMAT_MOD_LINEAR) &&
      pl_fmt_has_modifier (fmt, DRM_FORMAT_MOD_LINEAR)) {
    chosen[n++] = DRM_FORMAT_MOD_LINEAR;
  }
  if (!n) {
    logf_ (ROG_DOVI_LOG_WARN, "output %.4s: no modifier both the rendering device and the caller accept%s",
        (const char *) &out->drm_fourcc, render_node (s) == s->output_node ? "" : " (linear required across devices)");
    *declined = true;
    return NULL;
  }
  struct gbm_bo *bo = gbm_bo_create_with_modifiers2 (s->gbm, out->width, out->height,
      out->drm_fourcc, chosen, n, GBM_BO_USE_RENDERING);
  if (!bo) {
    logf_ (ROG_DOVI_LOG_WARN, "output %.4s %ux%u: GBM allocation failed: %s",
        (const char *) &out->drm_fourcc, out->width, out->height, strerror (errno));
    *declined = render_node (s) != s->output_node;
    return NULL;
  }
  out->modifier = gbm_bo_get_modifier (bo);
  out->num_planes = 1;
  out->planes[0] = (struct rog_dovi_dmabuf_plane) {
    .fd = -1, .offset = gbm_bo_get_offset (bo, 0), .pitch = gbm_bo_get_stride_for_plane (bo, 0) };
  *fd = gbm_bo_get_fd (bo);
  gbm_bo_destroy (bo);
  if (*fd < 0) return NULL;
  off_t end = lseek (*fd, 0, SEEK_END);
  pl_tex tex = end > 0 ? pl_tex_create (gpu, pl_tex_params (
      .w = (int) out->width, .h = (int) out->height, .format = fmt,
      .renderable = true, .storable = fmt->caps & PL_FMT_CAP_STORABLE,
      .blit_dst = fmt->caps & PL_FMT_CAP_BLITTABLE,
      .import_handle = PL_HANDLE_DMA_BUF,
      .shared_mem = {
        .handle.fd = *fd, .size = (size_t) end, .offset = out->planes[0].offset,
        .drm_format_mod = out->modifier, .stride_w = out->planes[0].pitch,
      })) : NULL;
  if (!tex) {
    logf_ (ROG_DOVI_LOG_WARN, "output %.4s modifier 0x%llx: the rendering device cannot import it",
        (const char *) &out->drm_fourcc, (unsigned long long) out->modifier);
    close (*fd); *fd = -1;
    *declined = render_node (s) != s->output_node;
  }
  return tex;
}

/* An imported output described like the AVFrame-built host destination
 * (pl_frame_from_avframe on the same AVFrame fields), on its own texture. */
static void describe_imported (struct pl_frame *frame, const AVFrame *like, pl_tex tex)
{
  pl_frame_from_avframe (frame, like);
  frame->num_planes = 1;
  frame->planes[0].texture = tex;
  int depth = tex->params.format->component_depth[0];
  if (depth != frame->repr.bits.sample_depth)
    frame->repr.bits = (struct pl_bit_encoding) {.sample_depth = depth, .color_depth = depth};
}

/* ---- Rendering (GTK: mapper.c render_destination) ---------------------- */
struct source {
  const struct rog_dovi_planes *planes;     /* host route */
  const struct rog_dovi_dmabuf *dmabuf;     /* DMABuf route */
};

static int render_destination (rog_dovi_mapper *s, const struct source *in,
    const struct rog_dovi_planes *fel_planes, const struct rog_dovi_picture *record,
    const struct rog_dovi_target *t, struct rog_dovi_output *output, bool sdr,
    uint32_t flags, const char **error)
{
  const AVDOVIMetadata *resolved = record_metadata (record);
  const uint8_t *raw = record && record->rpu && record->rpu_size ? record->rpu : NULL;
  const struct rog_dovi_stream_config *configuration;
  config_from_record (record, &configuration);
  bool profile5 = rog_dovi_map_profile5_has_no_base_fallback (configuration);
  bool host_output = output->kind == ROG_DOVI_OUTPUT_HOST;
  if (!profile5_destination_supported (configuration, sdr, t))
    return fail (s, error, ROG_DOVI_FAILURE_CONTENT,
        "Profile 5 needs an explicit SDR destination or a current native HDR witness");
  const struct rog_dovi_planes *p = in->planes;
  const struct rog_dovi_dmabuf *d = in->dmabuf;
  uint32_t width = p ? p->width : d->width, height = p ? p->height : d->height;
  bool has_crop = p && p->has_crop;
  enum AVPixelFormat format = p ? av_format (p->format) :
      d->drm_fourcc == DRM_FORMAT_P010 ? AV_PIX_FMT_P010LE :
      d->drm_fourcc == DRM_FORMAT_NV12 ? AV_PIX_FMT_NV12 : AV_PIX_FMT_NONE;
  bool output_ok = host_output ?
      output->host_format == (sdr ? ROG_DOVI_FORMAT_RGBA : ROG_DOVI_FORMAT_RGBA64LE) && output->acquire :
      output->kind == ROG_DOVI_OUTPUT_DMABUF && (sdr ?
          output->drm_fourcc == DRM_FORMAT_ABGR8888 || output->drm_fourcc == DRM_FORMAT_ABGR2101010 :
          output->drm_fourcc == DRM_FORMAT_ABGR16161616 || output->drm_fourcc == DRM_FORMAT_ABGR2101010);
  if (format == AV_PIX_FMT_NONE || !output_ok || (d && d->num_planes != 2))
    return fail (s, error, ROG_DOVI_FAILURE_INTERNAL, "Unsupported native plane import");
  if (!output->width || !output->height)
    return fail (s, error, ROG_DOVI_FAILURE_INTERNAL, "Invalid output size");
  AVFrame *src = NULL, *dst = av_frame_alloc (), *converted = NULL;
  struct pl_frame source = {0}, enhancement = {0}, destination = {0};
  AVFrame *fel = NULL;
  bool el_uploaded = false, uploaded = false, success = false, direct_output = false;
  pl_tex imported = NULL;
  int output_fd = -1;
  void *out_data = NULL;
  int32_t out_stride = 0;
  bool out_acquired = false;
  uint32_t storage_width = p ? p->storage_width : d->width;
  uint32_t storage_height = p ? p->storage_height : d->height;
  uint32_t picture_flags = p ? p->flags : d->flags;
  if (!dst) goto done;
  if (has_crop && (p->crop_x > storage_width || p->crop_y > storage_height ||
      p->crop_width != width || p->crop_height != height ||
      p->crop_width > storage_width - p->crop_x || p->crop_height > storage_height - p->crop_y)) goto done;
  bool native_yuv = format == AV_PIX_FMT_NV12 || format == AV_PIX_FMT_P010LE ||
      format == AV_PIX_FMT_YUV420P || format == AV_PIX_FMT_YUV420P10LE;
  const uint32_t witness = ROG_DOVI_TARGET_VALID | ROG_DOVI_TARGET_RENDER_READY | ROG_DOVI_TARGET_COMPOSED;
  bool apply_dovi = native_yuv && resolved && raw && t &&
      (sdr || (t->flags & witness) == witness) &&
      !(picture_flags & (ROG_DOVI_PICTURE_INTERLACED | ROG_DOVI_PICTURE_CORRUPTED |
          ROG_DOVI_PICTURE_ALT_LINE_CHROMA)) &&
      luma_depth (format) == av_dovi_get_header (resolved)->bl_bit_depth;
  if (!apply_dovi) decline (s, ROG_DOVI_DECLINE_NOT_ELIGIBLE);
  if (apply_dovi) {
    uint32_t native_width = record->width, native_height = record->height;
    const struct rog_dovi_geometry *geometry = record->has_geometry ? &record->geometry : NULL;
    const AVPixFmtDescriptor *desc = av_pix_fmt_desc_get (format);
    bool geometry_ok = geometry && native_width == width && native_height == height &&
        native_width == geometry->width && native_height == geometry->height;
    if (geometry_ok && has_crop) {
      geometry_ok = storage_width >= geometry->coded_width && storage_height >= geometry->coded_height &&
          p->crop_x == geometry->x && p->crop_y == geometry->y &&
          p->crop_width == geometry->width && p->crop_height == geometry->height &&
          !(p->crop_x & ((1u << desc->log2_chroma_w) - 1)) &&
          !(p->crop_y & ((1u << desc->log2_chroma_h) - 1)) &&
          !(p->crop_width & ((1u << desc->log2_chroma_w) - 1)) &&
          !(p->crop_height & ((1u << desc->log2_chroma_h) - 1));
    } else if (geometry_ok) {
      geometry_ok = storage_width == width && storage_height == height;
    }
    uint32_t profile = record->profile;
    const struct rog_dovi_stream_config *config = configuration;
    uint32_t residual = record->enhancement;
    bool paired_fel = profile == 7 && config && config->el_present &&
        config->bl_signal_compatibility_id == 6 &&
        residual == ROG_DOVI_ENHANCEMENT_UNRECONSTRUCTED && fel_planes;
    bool single_layer = config && !config->el_present &&
        residual == ROG_DOVI_ENHANCEMENT_NOT_REQUIRED &&
        ((profile == 5 && config->bl_signal_compatibility_id == 0) ||
         (profile == 8 && config->bl_signal_compatibility_id == 1));
    apply_dovi = (paired_fel || single_layer) && geometry_ok && config && config->version_major == 1 &&
        config->version_minor == 0 && config->profile == profile && config->bl_present &&
        config->rpu_present && config->md_compression == AV_DOVI_COMPRESSION_NONE;
    if (!apply_dovi) decline (s, ROG_DOVI_DECLINE_UNQUALIFIED);
  }
  if (apply_dovi && (!isfinite (t->max_nits) || !isfinite (t->min_nits) ||
      t->max_nits <= (sdr ? 0 : 203) || t->min_nits < 0 || t->min_nits >= t->max_nits)) {
    apply_dovi = false; decline (s, ROG_DOVI_DECLINE_TARGET);
  }
  /* Reuse the reviewed mpv physical transport law only for an actual PQ
   * buffer declaration with the standard203cd/m2 reference and10000maximum.
   * Creative trims use the physical target, never the normalized envelope. */
  if (apply_dovi) {
    double gain = ((double) PL_COLOR_SDR_WHITE / t->reference_nits) * (t->encoding_max_nits / 10000.0);
    double peak = t->max_nits * gain, black = t->min_nits * gain;
    apply_dovi = isfinite (t->reference_nits) && t->reference_nits > 0 &&
        t->encoding_reference_nits == PL_COLOR_SDR_WHITE && t->encoding_max_nits == 10000 &&
        isfinite (gain) && gain > 0 && isfinite (peak) && peak <= 10000 &&
        isfinite (black) && (t->min_nits == 0 || (float) black > 0);
    struct pl_raw_primaries prim = {
      .red = {t->primaries[0], t->primaries[1]}, .green = {t->primaries[2], t->primaries[3]},
      .blue = {t->primaries[4], t->primaries[5]}, .white = {t->primaries[6], t->primaries[7]},
    };
    for (unsigned i = 0; i < 8; i++) apply_dovi &= isfinite (t->primaries[i]);
    apply_dovi &= pl_primaries_valid (&prim);
    s->transport_gain = gain;
    if (!apply_dovi) decline (s, ROG_DOVI_DECLINE_TRANSPORT);
  }
  if (profile5 && !apply_dovi) {
    fail (s, error, ROG_DOVI_FAILURE_CONTENT, "Profile 5 cannot use ordinary base-layer color conversion");
    goto done;
  }
  if (!apply_dovi && !(flags & ROG_DOVI_MAP_BASELINE_ON_DECLINE)) { success = true; goto done; }
  if (p) {
    src = av_frame_alloc ();
    if (!src) goto done;
    bool active_import = apply_dovi && has_crop;
    uint32_t source_width = has_crop && !active_import ? storage_width : width;
    uint32_t source_height = has_crop && !active_import ? storage_height : height;
    src->format = format; src->width = (int) source_width; src->height = (int) source_height;
    src->color_range = p->color_range;
    src->color_primaries = p->color_primaries;
    src->color_trc = p->color_trc;
    src->colorspace = p->colorspace;
    src->chroma_location = p->chroma_location;
    src->sample_aspect_ratio = (AVRational) {p->sar_num, p->sar_den};
    if (av_frame_get_buffer (src, 32) < 0) goto done;
    const AVPixFmtDescriptor *desc = av_pix_fmt_desc_get (format);
    const uint8_t *planes[4] = {0}; int strides[4] = {0};
    int num_planes = av_pix_fmt_count_planes (format);
    for (int i = 0; i < num_planes; i++) {
      planes[i] = p->data[i];
      strides[i] = p->stride[i];
      if (active_import) {
        int component = 0;
        while (component < desc->nb_components && desc->comp[component].plane != i) component++;
        if (component == desc->nb_components) goto done;
        bool chroma = component == 1 || component == 2;
        planes[i] += (ptrdiff_t) (p->crop_y >> (chroma ? desc->log2_chroma_h : 0)) * strides[i] +
            (ptrdiff_t) (p->crop_x >> (chroma ? desc->log2_chroma_w : 0)) * desc->comp[component].step;
      }
    }
    av_image_copy (src->data, src->linesize, planes, strides, format, (int) source_width, (int) source_height);
  }
  if (!ensure_device (s)) goto done;
  if (d && !(src = dmabuf_avframe (s, d))) goto done;
  if (apply_dovi && !s->provider) s->provider = dv_provider387_create (s->vk->gpu, shared_log ());
  if (apply_dovi && !s->provider) goto done;
  if (!pl_map_avframe_ex (s->vk->gpu, &source,
      pl_avframe_params (.frame = src, .tex = s->source, .map_dovi = false))) goto done;
  uploaded = true;
  if (has_crop && !(apply_dovi && has_crop))
    source.crop = (struct pl_rect2df) {p->crop_x, p->crop_y, p->crop_x + p->crop_width, p->crop_y + p->crop_height};
  struct pl_frame baseline = source;
  struct pl_dovi_metadata dovi;
  if (apply_dovi) {
    pl_map_avdovi_metadata (&source.color, &source.repr, &dovi, resolved);
    /* The renderer samples an enhancement layer only for an active NLQ and
     * itself decides whether the master is reconstructed: a provably zero
     * residual (Profile 7 MEL) is complete without one. requires_fel below
     * still lets the provider map only a master the renderer calls composed. */
    if (fel_planes && dovi.nlq_active) {
      fel = av_frame_alloc ();
      enum AVPixelFormat fel_format = av_format (fel_planes->format);
      if (fel && fel_format != AV_PIX_FMT_NONE) {
        /* Borrowed planes, uploaded as they are: no AVBufferRefs to free. */
        fel->format = fel_format;
        fel->width = (int) fel_planes->width; fel->height = (int) fel_planes->height;
        fel->color_range = fel_planes->color_range;
        fel->color_primaries = fel_planes->color_primaries;
        fel->color_trc = fel_planes->color_trc;
        fel->colorspace = fel_planes->colorspace;
        fel->chroma_location = fel_planes->chroma_location;
        fel->sample_aspect_ratio = (AVRational) {fel_planes->sar_num, fel_planes->sar_den};
        for (int i = 0; i < 4; i++) {
          fel->data[i] = (uint8_t *) fel_planes->data[i];
          fel->linesize[i] = fel_planes->stride[i];
        }
      }
      if (fel && fel_format != AV_PIX_FMT_NONE && pl_map_avframe_ex (s->vk->gpu, &enhancement,
          pl_avframe_params (.frame = fel, .tex = s->enhancement, .map_dovi = false))) {
        el_uploaded = true;
        source.enhancement_layer = &enhancement;
      } else {
        apply_dovi = false;
        source = baseline;
        decline (s, ROG_DOVI_DECLINE_ENHANCEMENT);
      }
    }
  }
  if (profile5 && !apply_dovi) {
    fail (s, error, ROG_DOVI_FAILURE_CONTENT, "Profile 5 cannot use ordinary base-layer color conversion");
    goto done;
  }
  if (!apply_dovi && !(flags & ROG_DOVI_MAP_BASELINE_ON_DECLINE)) { success = true; goto done; }
  if (apply_dovi) {
    source.dovi_rpu = raw;
    source.dovi_rpu_size = record->rpu_size;
    source.dovi_master_width = (int) width; source.dovi_master_height = (int) height;
  }
  dst->format = AV_PIX_FMT_RGBA64LE; dst->width = (int) output->width; dst->height = (int) output->height;
  dst->color_range = host_output && !sdr ? output->color_range : AVCOL_RANGE_JPEG;
  dst->colorspace = AVCOL_SPC_RGB;
  dst->color_primaries = AVCOL_PRI_BT2020; dst->color_trc = AVCOL_TRC_SMPTE2084;
  if (sdr) {
    /* The intermediate remains PQ16. Its layout must never borrow the final
     * eight-bit SDR output, whose authoritative layout is different. */
    if (av_frame_get_buffer (dst, 32) < 0) goto done;
  } else if (host_output) {
    if (!output->acquire (output->acquire_user, &out_data, &out_stride) || !out_data) goto done;
    out_acquired = true;
    /* Borrow the owned output memory; dst has no AVBufferRefs to free it. */
    dst->data[0] = out_data;
    dst->linesize[0] = out_stride;
  } else {
    bool output_declined;
    imported = allocate_output (s, output, &output_fd, &output_declined);
    if (!imported) {
      if (output_declined) {
        decline (s, ROG_DOVI_DECLINE_OUTPUT_IMPORT);
        if (profile5) fail (s, error, ROG_DOVI_FAILURE_CONTENT,
            "Profile 5 output cannot be imported by the output node");
        else { apply_dovi = false; success = true; }
      }
      goto done;
    }
  }
  if (!sdr && !host_output) describe_imported (&destination, dst, imported);
  else if (!pl_frame_recreate_from_avframe (s->vk->gpu, &destination, s->output, dst)) goto done;
  /* Render targets recreated for download are not sampleable, but the SDR
   * destination reads the graded PQ picture back in a second pass. Give that
   * intermediate its own stable textures with the same layout, sampleable. */
  for (int i = 0; sdr && i < destination.num_planes; i++) {
    struct pl_tex_params params = destination.planes[i].texture->params;
    params.sampleable = true;
    if (!(params.format->caps & PL_FMT_CAP_SAMPLEABLE) ||
        !pl_tex_recreate (s->vk->gpu, &s->sdr_intermediate[i], &params)) goto done;
    destination.planes[i].texture = s->sdr_intermediate[i];
  }
  direct_output = !sdr && host_output && direct_output_layout (out_stride, output->width, 8, &destination);
  if (!sdr && host_output && !direct_output) {
    /* Keep valid bottom-up or GPU-incompatible custom rows on the existing
     * canonical download-and-copy path. Never pass a signed pitch as size_t. */
    memset (dst->data, 0, sizeof (dst->data));
    memset (dst->linesize, 0, sizeof (dst->linesize));
    if (av_frame_get_buffer (dst, 32) < 0 ||
        !pl_frame_recreate_from_avframe (s->vk->gpu, &destination, s->output, dst)) goto done;
    if (!download_row_pitch_ok (dst->linesize[0],
            destination.planes[0].texture->params.format->texel_align, (size_t) dst->width * 8)) goto done;
  }
  for (int i = 0; i < destination.num_planes; i++) {
    const float zero[4] = {0}; pl_tex_clear (s->vk->gpu, destination.planes[i].texture, zero);
  }
  struct pl_color_space baseline_destination = destination.color;
  struct pl_render_params params = pl_render_default_params;
  if (apply_dovi) {
    destination.color.hdr.min_luma = t->min_nits;
    destination.color.hdr.max_luma = t->max_nits;
    destination.color.hdr.prim = (struct pl_raw_primaries) {
      .red = {t->primaries[0], t->primaries[1]}, .green = {t->primaries[2], t->primaries[3]},
      .blue = {t->primaries[4], t->primaries[5]}, .white = {t->primaries[6], t->primaries[7]},
    };
    s->physical = destination.color;
    destination.color.hdr.min_luma *= s->transport_gain;
    destination.color.hdr.max_luma *= s->transport_gain;
    params.dovi_map = provider_map; params.dovi_priv = s;
    params.dovi_signature = t->generation;
  }
  s->requires_fel = apply_dovi && fel_planes;
  s->mapped = 0;
  if (!pl_render_image (s->renderer, &source, &destination, &params)) goto done;
  if (apply_dovi && s->mapped == 0) {
    if (profile5) {
      fail (s, error, ROG_DOVI_FAILURE_CONTENT,
          "Profile 5 mapping was declined; ordinary base-layer conversion is unsupported");
      goto done;
    }
    /* The provider can decline compressed/unqualified creative metadata.
     * Reproduce the ordinary input interpretation, then encode it as PQ;
     * do not call a normalized-but-ungraded image the stock fallback. */
    decline (s, ROG_DOVI_DECLINE_PROVIDER);
    if (!(flags & ROG_DOVI_MAP_BASELINE_ON_DECLINE)) { success = true; goto done; }
    params.dovi_map = NULL; params.dovi_priv = NULL;
    destination.color = baseline_destination;
    if (!pl_render_image (s->renderer, &baseline, &destination, &params)) goto done;
  }
  if (s->mapped < 0) goto done;
  if (sdr) {
    converted = av_frame_alloc ();
    if (!converted) goto done;
    converted->format = AV_PIX_FMT_RGBA;
    converted->width = dst->width; converted->height = dst->height;
    converted->color_range = AVCOL_RANGE_JPEG; converted->colorspace = AVCOL_SPC_RGB;
    converted->color_primaries = AVCOL_PRI_BT709;
    converted->color_trc = AVCOL_TRC_IEC61966_2_1;
    struct pl_frame sdr_destination = {0};
    if (host_output) {
      if (!output->acquire (output->acquire_user, &out_data, &out_stride) || !out_data) goto done;
      out_acquired = true;
      converted->data[0] = out_data;
      converted->linesize[0] = out_stride;
      if (!pl_frame_recreate_from_avframe (s->vk->gpu, &sdr_destination,
              s->sdr_output, converted)) goto done;
      direct_output = direct_output_layout (out_stride, output->width, 4, &sdr_destination);
      if (!direct_output) {
        memset (converted->data, 0, sizeof (converted->data));
        memset (converted->linesize, 0, sizeof (converted->linesize));
        if (av_frame_get_buffer (converted, 32) < 0 ||
            !pl_frame_recreate_from_avframe (s->vk->gpu, &sdr_destination,
                s->sdr_output, converted)) goto done;
        if (!download_row_pitch_ok (converted->linesize[0],
                sdr_destination.planes[0].texture->params.format->texel_align,
                (size_t) converted->width * 4)) goto done;
      }
    } else {
      bool output_declined;
      imported = allocate_output (s, output, &output_fd, &output_declined);
      if (!imported) {
        if (output_declined) {
          decline (s, ROG_DOVI_DECLINE_OUTPUT_IMPORT);
          if (profile5) fail (s, error, ROG_DOVI_FAILURE_CONTENT,
              "Profile 5 output cannot be imported by the output node");
          else { s->mapped = 0; success = true; }
        }
        goto done;
      }
      describe_imported (&sdr_destination, converted, imported);
    }
    pl_shader sh = pl_dispatch_begin (s->dispatch);
    if (!pl_shader_sample_direct (sh,
        pl_sample_src (.tex = destination.planes[0].texture))) {
      pl_dispatch_abort (s->dispatch, &sh); goto done;
    }
    const struct pl_color_space pq = {
      .primaries = PL_COLOR_PRIM_BT_2020, .transfer = PL_COLOR_TRC_PQ};
    const struct pl_color_space srgb = {
      .primaries = PL_COLOR_PRIM_BT_709, .transfer = PL_COLOR_TRC_SRGB};
    /* Public D65 Rec.2020 -> Rec.709 linear matrix. The explicit100nit target
     * is normalized by the existing PQ transport law; gamut conversion occurs
     * before clipping and the sRGB transfer is applied exactly once. */
    pl_shader_linearize (sh, &pq);
    if (!pl_shader_custom (sh, &(struct pl_custom_shader) {
        .description = "explicit100nit BT709 SDR video destination",
        .body = "color.rgb = clamp(mat3(1.6604910021, -0.1245504745, -0.0181507634, "
                "-0.5876411388, 1.1328998971, -0.1005788980, "
                "-0.0728498633, -0.0083494226, 1.1187296614) * color.rgb, 0.0, 1.0);",
        .input = PL_SHADER_SIG_COLOR, .output = PL_SHADER_SIG_COLOR})) {
      pl_dispatch_abort (s->dispatch, &sh); goto done;
    }
    pl_shader_delinearize (sh, &srgb);
    if (!pl_dispatch_finish (s->dispatch, pl_dispatch_params (
        .shader = &sh, .target = sdr_destination.planes[0].texture))) goto done;
    if (host_output && !pl_download_avframe (s->vk->gpu, &sdr_destination, converted)) goto done;
  } else if (host_output && !pl_download_avframe (s->vk->gpu, &destination, dst)) goto done;
  /* Download blocks until the borrowed output write is complete. */
  if (host_output && !direct_output) {
    AVFrame *final = sdr ? converted : dst;
    uint8_t *planes[4] = {out_data};
    int strides[4] = {out_stride};
    av_image_copy (planes, strides, (const uint8_t **) final->data, final->linesize,
        (enum AVPixelFormat) final->format, final->width, final->height);
  }
  if (!host_output) {
    /* The caller presents the buffer as soon as this returns. */
    pl_gpu_finish (s->vk->gpu);
    output->planes[0].fd = output_fd;
    output_fd = -1;
  }
  success = true;
done:
  if (imported) pl_tex_destroy (s->vk->gpu, &imported);
  if (output_fd >= 0) close (output_fd);
  if (el_uploaded) pl_unmap_avframe (s->vk->gpu, &enhancement);
  if (uploaded) pl_unmap_avframe (s->vk->gpu, &source);
  av_frame_free (&src); av_frame_free (&dst); av_frame_free (&converted); av_frame_free (&fel);
  (void) out_acquired;
  if (!success) {
    if (!host_output) output->num_planes = 0;
    return fail (s, error, ROG_DOVI_FAILURE_INTERNAL, "Eligible Dolby frame normalization/mapping failed");
  }
  if (s->mapped != 1 && !host_output && output->planes[0].fd < 0) output->num_planes = 0;
  return s->mapped == 1 && apply_dovi ? 1 : 0;
}

/* The logical SDR destination (GTK: gst_gtk_dovi_mapper_render_destination).
 * Native validity/composition/readiness flags deliberately remain clear. */
static const struct rog_dovi_target logical_sdr = {
  .struct_size = sizeof (struct rog_dovi_target),
  .generation = 1, .primaries = {.64,.33,.30,.60,.15,.06,.3127,.3290},
  .min_nits = 0, .max_nits = 100, .reference_nits = 100,
  .encoding_reference_nits = 203, .encoding_max_nits = 10000,
};

static int map (rog_dovi_mapper *s, const struct source *in,
    const struct rog_dovi_planes *enhancement, const struct rog_dovi_picture *record,
    enum rog_dovi_destination kind, const struct rog_dovi_target *physical,
    struct rog_dovi_output *output, uint32_t flags, const char **error)
{
  if (error) *error = NULL;
  if (!s) return fail (s, error, ROG_DOVI_FAILURE_INTERNAL, "No mapper");
  s->declined = 0;
  s->failure = ROG_DOVI_FAILURE_NONE;
  if (!output || output->struct_size < sizeof (*output) ||
      (record && record->struct_size < sizeof (*record)) ||
      (physical && physical->struct_size < sizeof (*physical)) ||
      (enhancement && enhancement->struct_size < sizeof (*enhancement)))
    return fail (s, error, ROG_DOVI_FAILURE_INTERNAL, "Invalid arguments");
  if (output->kind == ROG_DOVI_OUTPUT_DMABUF) {
    output->num_planes = 0;
    for (int i = 0; i < 4; i++) output->planes[i].fd = -1;
  }
  bool sdr = kind == ROG_DOVI_DESTINATION_STANDARD_SDR_SRGB;
  if (!sdr && kind != ROG_DOVI_DESTINATION_DISPLAY_PQ)
    return fail (s, error, ROG_DOVI_FAILURE_INTERNAL, "Unsupported destination kind");
  if (s->has_destination && s->last_sdr_destination != sdr && s->renderer)
    pl_renderer_flush_cache (s->renderer);
  s->has_destination = true;
  s->last_sdr_destination = sdr;
  return render_destination (s, in, enhancement, record, sdr ? &logical_sdr : physical,
      output, sdr, flags, error);
}

int rog_dovi_map_planes (rog_dovi_mapper *s, const struct rog_dovi_planes *picture,
    const struct rog_dovi_planes *enhancement, const struct rog_dovi_picture *record,
    enum rog_dovi_destination destination, const struct rog_dovi_target *target,
    struct rog_dovi_output *output, uint32_t flags, const char **error)
{
  if (!picture || picture->struct_size < sizeof (*picture)) {
    if (error) *error = NULL;
    return fail (s, error, ROG_DOVI_FAILURE_INTERNAL, "Invalid arguments");
  }
  const struct source in = {.planes = picture};
  return map (s, &in, enhancement, record, destination, target, output, flags, error);
}

int rog_dovi_map_dmabuf (rog_dovi_mapper *s, const struct rog_dovi_dmabuf *picture,
    const struct rog_dovi_planes *enhancement, const struct rog_dovi_picture *record,
    enum rog_dovi_destination destination, const struct rog_dovi_target *target,
    struct rog_dovi_output *output, uint32_t flags, const char **error)
{
  if (!picture || picture->struct_size < sizeof (*picture)) {
    if (error) *error = NULL;
    return fail (s, error, ROG_DOVI_FAILURE_INTERNAL, "Invalid arguments");
  }
  const struct source in = {.dmabuf = picture};
  return map (s, &in, enhancement, record, destination, target, output, flags, error);
}
