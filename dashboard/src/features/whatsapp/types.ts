export interface WAContactSummary {
  id: string;
  phone_e164: string;
  display_name: string | null;
}

export interface WAConversation {
  id: string;
  status: 'open' | 'assigned' | 'snoozed' | 'closed' | 'expired';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  assignee_user_id: string | null;
  last_message_text: string | null;
  last_message_at: string | null;
  last_inbound_at: string | null;
  last_outbound_at: string | null;
  window_expires_at: string | null;
  unread_count: number;
  message_count: number;
  created_at: string;
  updated_at: string;
  contact: WAContactSummary;
  contact_tags: WATag[];
  contact_segments: { id: string; name: string; color: string }[];
}

export interface WAMessage {
  id: string;
  direction: 'inbound' | 'outbound';
  msg_type: string;
  text_body: string | null;
  media_url: string | null;
  media_mime_type: string | null;
  media_caption: string | null;
  delivery_status: 'pending' | 'sent' | 'delivered' | 'read' | 'failed';
  is_from_ai: boolean;
  sender_phone: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  read_at: string | null;
  created_at: string;
}

export interface WAConversationListResponse {
  items: WAConversation[];
  total: number;
}

export interface WAMessageListResponse {
  items: WAMessage[];
  has_more: boolean;
  next_cursor: string | null;
}

// Phase A: Segments, Tags, Notes, Contact Detail

export interface WASegment {
  id: string;
  name: string;
  slug: string;
  color: string;
  icon: string | null;
  description: string | null;
  is_system: boolean;
  contact_count: number;
  sort_order: number;
}

export interface WATag {
  id: string;
  name: string;
  color: string;
}

export interface WAInternalNote {
  id: string;
  author_user_id: string;
  author_name: string;
  content: string;
  created_at: string;
}

export interface WAContactDetail {
  id: string;
  phone_e164: string;
  display_name: string | null;
  email: string | null;
  opt_in_status: string;
  notes: string | null;
  source: string;
  metadata_extra: Record<string, unknown> | null;
  segments: WASegment[];
  tags: WATag[];
  created_at: string;
  updated_at: string;
}

export interface WAAgent {
  id: string;
  name: string;
  email: string | null;
  role: string;
}

export interface WASegmentListResponse {
  items: WASegment[];
}

export interface WATagListResponse {
  items: WATag[];
}

export interface WAInternalNoteListResponse {
  items: WAInternalNote[];
}

// Phase C: Templates

export interface WATemplate {
  id: string;
  name: string;
  language: string;
  category: string;
  status: 'draft' | 'pending' | 'approved' | 'rejected' | 'paused' | 'disabled';
  header_type: string | null;
  header_content: string | null;
  body_text: string;
  footer: string | null;
  buttons: Record<string, unknown> | null;
  variables: Record<string, unknown> | null;
  meta_template_id: string | null;
  meta_rejected_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface WATemplateListResponse {
  items: WATemplate[];
  total: number;
}

// Phase D: Campaigns

export interface WACampaignCatalogItem {
  id: string;
  name: string;
  price: number;
  currency: string;
  image_url: string | null;
  product_url: string | null;
  description: string | null;
  category: string | null;
}

export interface WACampaign {
  id: string;
  name: string;
  status: 'draft' | 'scheduled' | 'sending' | 'paused' | 'completed' | 'cancelled';
  template_id: string | null;
  template_name: string | null;
  catalog_item_id: string | null;
  catalog_item: WACampaignCatalogItem | null;
  audience_filter: Record<string, unknown> | null;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  is_ab_test: boolean;
  total_recipients: number;
  sent_count: number;
  delivered_count: number;
  read_count: number;
  failed_count: number;
  created_at: string;
  updated_at: string;
}

export interface WACampaignListResponse {
  items: WACampaign[];
  total: number;
}

export interface WACampaignRecipient {
  id: string;
  contact_id: string;
  contact_name: string | null;
  contact_phone: string | null;
  status: string;
  sent_at: string | null;
  delivered_at: string | null;
  read_at: string | null;
  error_detail: string | null;
}

// Phase E: Pipeline + CRM

export interface WAPipelineStage {
  id: string;
  name: string;
  color: string;
  sort_order: number;
  is_default: boolean;
  is_won: boolean;
  is_lost: boolean;
  deal_count: number;
  deal_value: number;
}

export interface WADeal {
  id: string;
  stage_id: string;
  stage_name: string | null;
  contact_id: string | null;
  contact_name: string | null;
  contact_phone: string | null;
  conversation_id: string | null;
  title: string;
  value: number;
  currency: string;
  assignee_user_id: string | null;
  expected_close_date: string | null;
  closed_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface WADealListResponse {
  items: WADeal[];
  total: number;
}

export interface WAPipelineAnalytics {
  total_deals: number;
  total_value: number;
  won_deals: number;
  won_value: number;
  lost_deals: number;
  conversion_rate: number;
  stages: WAPipelineStage[];
}

// Phase F: Commerce

export interface WACatalogItem {
  id: string;
  name: string;
  description: string | null;
  price: number;
  currency: string;
  image_url: string | null;
  product_url: string | null;
  category: string | null;
  sku: string | null;
  stock: number | null;
  status: 'active' | 'inactive' | 'out_of_stock';
  created_at: string;
  updated_at: string;
}

export interface WACatalogItemListResponse {
  items: WACatalogItem[];
  total: number;
}

export interface WAOrderItem {
  id: string;
  catalog_item_id: string | null;
  name: string;
  quantity: number;
  unit_price: number;
}

export interface WAOrder {
  id: string;
  contact_id: string | null;
  contact_name: string | null;
  contact_phone: string | null;
  conversation_id: string | null;
  status: 'pending' | 'confirmed' | 'processing' | 'shipped' | 'delivered' | 'cancelled' | 'refunded';
  total: number;
  currency: string;
  notes: string | null;
  items: WAOrderItem[];
  created_at: string;
  updated_at: string;
}

export interface WAOrderListResponse {
  items: WAOrder[];
  total: number;
}

// Automation: Macros

export interface WAMacro {
  id: string;
  name: string;
  shortcut: string | null;
  text: string;
  category: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

// Automation: SLA

export interface WASlaPolicy {
  id: string;
  name: string;
  first_response_minutes: number;
  resolution_minutes: number;
  priority: string;
  is_active: boolean;
  escalation_email: string | null;
  business_hours_only: boolean;
  created_at: string;
  updated_at: string;
}

export interface WASlaBreach {
  id: string;
  conversation_id: string;
  policy_id: string;
  breach_type: string;
  breached_at: string;
  resolved_at: string | null;
}

// Automation: Webhooks

export interface WAWebhookConfig {
  id: string;
  name: string;
  url: string;
  events: string[];
  is_active: boolean;
  headers: Record<string, string> | null;
  last_triggered_at: string | null;
  failure_count: number;
  created_at: string;
  updated_at: string;
}

export interface WAWebhookLog {
  id: string;
  webhook_id: string;
  event_type: string;
  response_code: number | null;
  success: boolean;
  sent_at: string;
}

// Automation: Surveys

export interface WASurvey {
  id: string;
  name: string;
  survey_type: string;
  questions: Record<string, unknown>;
  trigger: string;
  is_active: boolean;
  response_count: number;
  avg_score: number | null;
  created_at: string;
  updated_at: string;
}

export interface WASurveyAnswer {
  id: string;
  survey_id: string;
  contact_id: string | null;
  answers: Record<string, unknown>;
  score: number | null;
  feedback: string | null;
  created_at: string;
}

// Automation: Flows

export interface WAFlow {
  id: string;
  name: string;
  description: string | null;
  trigger_type: string;
  trigger_config: Record<string, unknown> | null;
  steps: Record<string, unknown>;
  is_active: boolean;
  last_triggered_at: string | null;
  execution_count: number;
  created_at: string;
  updated_at: string;
}

// Integrations

export interface WAIntegration {
  id: string;
  integration_type: string;
  name: string;
  config: Record<string, unknown>;
  is_active: boolean;
  last_sync_at: string | null;
  status_message: string | null;
  created_at: string;
  updated_at: string;
}

// Widget Web

export interface WAWidgetConfig {
  id: string;
  is_active: boolean;
  primary_color: string;
  welcome_message: string;
  position: string;
  auto_open_seconds: number;
  allowed_domains: string[] | null;
  avatar_url: string | null;
  business_name: string | null;
  offline_message: string;
  created_at: string;
  updated_at: string;
}

// Dashboard Overview

export interface WADashboardOverview {
  conversations: {
    total: number;
    open: number;
    closed: number;
    unassigned: number;
  };
  messages_today: {
    inbound: number;
    outbound: number;
  };
  contacts_total: number;
  active_campaigns: number;
  sla_breaches_unresolved: number;
  avg_response_minutes: number | null;
}

// Audit

export interface WAAuditLogEntry {
  id: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string | null;
  provider_event_id: string | null;
}

// Admin BSP

export interface WAAdminOverview {
  tenant_id: string;
  settings: {
    phone_number_id: string | null;
    business_account_id: string | null;
    display_phone: string | null;
    webhook_verify_token: string | null;
    is_configured: boolean;
  };
  usage: Record<string, number>;
}

// Messaging Analytics

export interface WAMessagingAnalytics {
  period_days: number;
  messages: {
    inbound: number;
    outbound: number;
    templates: number;
    read: number;
    failed: number;
    active_conversations: number;
  };
  daily: { day: string; inbound: number; outbound: number }[];
  campaigns: {
    total: number;
    completed: number;
    total_sent: number;
    total_delivered: number;
    total_read: number;
  };
}
