import { useState, useEffect, useCallback } from 'react';
import type { WASegment } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useSidebar } from '../../../context/SidebarContext';
import type { SidebarSegment } from '../../../context/SidebarContext';

/** Map WASegment to SidebarSegment (sidebar only needs id, name, slug, contact_count). */
function toSidebarSegments(segments: WASegment[]): SidebarSegment[] {
  return segments.map(s => ({
    id: s.id,
    name: s.name,
    slug: s.slug ?? s.name.toLowerCase().replace(/\s+/g, '-'),
    icon: s.icon ?? undefined,
    contact_count: s.contact_count ?? 0,
  }));
}

export function useSegments() {
  const [segments, setSegments] = useState<WASegment[]>([]);
  const [loading, setLoading] = useState(true);
  const { activeSegmentId, setActiveSegmentId, setWhatsAppSegments } = useSidebar();

  const fetchSegments = useCallback(async () => {
    try {
      const data = await whatsappApi.getSegments();
      setSegments(data.items);
      setWhatsAppSegments(toSidebarSegments(data.items));
    } catch (err) {
      console.error('Failed to fetch segments:', err);
    } finally {
      setLoading(false);
    }
  }, [setWhatsAppSegments]);

  useEffect(() => {
    fetchSegments();
  }, [fetchSegments]);

  // Sync segments to sidebar context when they change
  useEffect(() => {
    setWhatsAppSegments(toSidebarSegments(segments));
  }, [segments, setWhatsAppSegments]);

  const createSegment = useCallback(async (data: { name: string; color?: string }) => {
    const segment = await whatsappApi.createSegment(data);
    setSegments(prev => [...prev, segment]);
    return segment;
  }, []);

  return {
    segments,
    loading,
    activeSegmentId,
    setActiveSegmentId,
    createSegment,
    refetch: fetchSegments,
  };
}
