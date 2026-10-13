import React, { useState } from 'react';
import type { WAOrder } from '../types';
import { whatsappApi } from '../services/whatsappApi';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';
import { usePaginatedFetch } from '../../../hooks/usePaginatedFetch';

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  pending: { label: 'Pendiente', color: 'bg-yellow-600' },
  confirmed: { label: 'Confirmado', color: 'bg-blue-600' },
  processing: { label: 'Procesando', color: 'bg-purple-600' },
  shipped: { label: 'Enviado', color: 'bg-cyan-600' },
  delivered: { label: 'Entregado', color: 'bg-green-600' },
  cancelled: { label: 'Cancelado', color: 'bg-red-600' },
  refunded: { label: 'Reembolsado', color: 'bg-orange-600' },
};

const STATUS_FLOW: Record<string, string[]> = {
  pending: ['confirmed', 'cancelled'], confirmed: ['processing', 'cancelled'],
  processing: ['shipped', 'cancelled'], shipped: ['delivered'],
  delivered: ['refunded'], cancelled: [], refunded: [],
};

const OrdersPage: React.FC = () => {
  const { toast } = useToast();
  const [statusFilter, setStatusFilter] = useState('');
  const [detailOrder, setDetailOrder] = useState<WAOrder | null>(null);
  const [confirmAction, setConfirmAction] = useState<{ orderId: string; newStatus: string } | null>(null);

  const { items: orders, total, loading, page, setPage, totalPages, refetch } = usePaginatedFetch<WAOrder>(
    (skip, limit, filters) => whatsappApi.getOrders({ status: filters.status, skip, limit }),
    { pageSize: 20, filters: { status: statusFilter || undefined } },
  );

  const handleStatusChange = async (orderId: string, newStatus: string) => {
    if (['cancelled', 'refunded'].includes(newStatus)) { setConfirmAction({ orderId, newStatus }); return; }
    await doStatusChange(orderId, newStatus);
  };

  const doStatusChange = async (orderId: string, newStatus: string) => {
    try {
      await whatsappApi.updateOrder(orderId, { status: newStatus });
      toast(`Pedido ${STATUS_LABELS[newStatus]?.label?.toLowerCase() || newStatus}`);
      refetch();
      if (detailOrder?.id === orderId) { try { setDetailOrder(await whatsappApi.getOrder(orderId)); } catch { /* empty */ } }
    } catch { toast('Error actualizando pedido', 'error'); }
  };

  const handleConfirmAction = async () => {
    if (!confirmAction) return;
    await doStatusChange(confirmAction.orderId, confirmAction.newStatus);
    setConfirmAction(null);
  };

  const formatDate = (iso: string) => new Date(iso).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });


  return (
    <div className="flex flex-col h-full p-6 gap-4">
      <div>
        <div className="flex items-center justify-between mb-1">
          <h1 className="text-2xl font-bold text-white">Pedidos</h1>
          <span className="text-xs text-gray-500">{total} pedidos</span>
        </div>
        <p className="text-gray-400 text-sm">Gestiona los pedidos recibidos por WhatsApp</p>
      </div>

      <div className="flex-1 min-h-64 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden flex flex-col">
        <div className="px-4 py-3 border-b border-gray-700">
          <div className="flex gap-2 flex-wrap">
            {['', 'pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded'].map(s => (
              <button key={s} onClick={() => { setStatusFilter(s); setPage(0); }}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium ${statusFilter === s ? 'bg-green-600/20 text-green-400 border border-green-500/30' : 'border border-gray-600 text-gray-400'}`}>
                {s ? (STATUS_LABELS[s]?.label || s) : 'Todos'}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-32"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" /></div>
          ) : orders.length === 0 ? (
            <div className="flex items-center justify-center h-32">
              <div className="bg-gray-900/50 border border-dashed border-gray-700 rounded-xl px-8 py-6 text-center">
                <p className="text-gray-500 text-sm">No hay pedidos</p>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              {orders.map(order => {
                const st = STATUS_LABELS[order.status] || { label: order.status, color: 'bg-gray-600' };
                const nextStates = STATUS_FLOW[order.status] || [];
                return (
                  <div key={order.id} className="bg-gray-900/50 rounded-xl border border-gray-700 p-4 hover:border-green-500/30 transition">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <button onClick={() => setDetailOrder(order)} className="text-sm font-medium text-white hover:text-green-400">#{order.id.slice(0, 8)}</button>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] text-white ${st.color}`}>{st.label}</span>
                        {order.contact_name && <span className="text-xs text-gray-400">{order.contact_name}</span>}
                        {order.contact_phone && <span className="text-[10px] text-gray-600">{order.contact_phone}</span>}
                      </div>
                      <span className="text-sm font-bold text-green-400">{Number(order.total).toLocaleString('es-ES', { minimumFractionDigits: 2 })} {order.currency}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4 text-[11px] text-gray-500">
                        <span>{order.items.length} {order.items.length === 1 ? 'producto' : 'productos'}</span>
                        <span>{formatDate(order.created_at)}</span>
                      </div>
                      {nextStates.length > 0 && (
                        <div className="flex gap-2">
                          {nextStates.map(ns => (
                            <button key={ns} onClick={() => handleStatusChange(order.id, ns)} className="text-xs text-gray-400 hover:text-white">
                              {STATUS_LABELS[ns]?.label || ns}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-gray-700 flex items-center justify-between text-sm text-gray-400">
            <span>{total} pedidos</span>
            <div className="flex gap-2">
              <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-700 hover:border-gray-600 transition disabled:opacity-50">Anterior</button>
              <span className="px-3 py-1.5">{page + 1} / {totalPages}</span>
              <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)} className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-700 hover:border-gray-600 transition disabled:opacity-50">Siguiente</button>
            </div>
          </div>
        )}
      </div>

      {detailOrder && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={e => e.target === e.currentTarget && setDetailOrder(null)}>
          <div className="bg-gray-800 rounded-2xl p-6 w-[520px] border border-gray-700 max-h-[80vh] overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-white font-bold">Pedido #{detailOrder.id.slice(0, 8)}</h2>
              <span className={`px-2 py-0.5 rounded text-xs text-white ${STATUS_LABELS[detailOrder.status]?.color || 'bg-gray-600'}`}>
                {STATUS_LABELS[detailOrder.status]?.label || detailOrder.status}
              </span>
            </div>
            {detailOrder.contact_name && (
              <div className="mb-4 text-sm">
                <span className="text-gray-500">Cliente: </span><span className="text-white">{detailOrder.contact_name}</span>
                {detailOrder.contact_phone && <span className="text-gray-500 ml-2">{detailOrder.contact_phone}</span>}
              </div>
            )}
            <div className="bg-gray-700/50 rounded-lg overflow-hidden mb-4">
              <table className="w-full text-sm">
                <thead><tr className="text-gray-500 text-xs border-b border-gray-700">
                  <th className="text-left px-3 py-2 font-medium">Producto</th>
                  <th className="text-right px-3 py-2 font-medium">Cant.</th>
                  <th className="text-right px-3 py-2 font-medium">Precio</th>
                  <th className="text-right px-3 py-2 font-medium">Subtotal</th>
                </tr></thead>
                <tbody>
                  {detailOrder.items.map(item => (
                    <tr key={item.id} className="border-b border-gray-700/50">
                      <td className="px-3 py-2 text-white">{item.name}</td>
                      <td className="px-3 py-2 text-right text-gray-400">{item.quantity}</td>
                      <td className="px-3 py-2 text-right text-gray-400">{Number(item.unit_price).toLocaleString('es-ES', { minimumFractionDigits: 2 })}</td>
                      <td className="px-3 py-2 text-right text-white">{(item.quantity * Number(item.unit_price)).toLocaleString('es-ES', { minimumFractionDigits: 2 })}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot><tr>
                  <td colSpan={3} className="px-3 py-2 text-right text-sm font-bold text-gray-400">Total</td>
                  <td className="px-3 py-2 text-right text-lg font-bold text-green-400">{Number(detailOrder.total).toLocaleString('es-ES', { minimumFractionDigits: 2 })} {detailOrder.currency}</td>
                </tr></tfoot>
              </table>
            </div>
            {detailOrder.notes && <div className="mb-4"><p className="text-xs text-gray-500 mb-1">Notas</p><p className="text-sm text-gray-300">{detailOrder.notes}</p></div>}
            <p className="text-[10px] text-gray-600 mb-4">Creado: {formatDate(detailOrder.created_at)}</p>
            {(STATUS_FLOW[detailOrder.status] || []).length > 0 && (
              <div className="flex gap-2 mb-4">
                {STATUS_FLOW[detailOrder.status].map(ns => (
                  <button key={ns} onClick={() => handleStatusChange(detailOrder.id, ns)}
                    className={`px-4 py-2 text-xs text-white rounded-lg ${STATUS_LABELS[ns]?.color || 'bg-gray-600'} hover:opacity-80 font-medium transition`}>
                    {STATUS_LABELS[ns]?.label || ns}
                  </button>
                ))}
              </div>
            )}
            <div className="flex justify-end"><button onClick={() => setDetailOrder(null)} className="px-4 py-2 text-sm text-gray-400 hover:text-white font-medium transition">Cerrar</button></div>
          </div>
        </div>
      )}

      <ConfirmDialog open={!!confirmAction}
        title={confirmAction?.newStatus === 'cancelled' ? 'Cancelar pedido' : 'Reembolsar pedido'}
        message={confirmAction?.newStatus === 'cancelled' ? '¿Seguro que quieres cancelar este pedido?' : '¿Seguro que quieres reembolsar este pedido?'}
        confirmLabel={confirmAction?.newStatus === 'cancelled' ? 'Cancelar pedido' : 'Reembolsar'}
        variant={confirmAction?.newStatus === 'cancelled' ? 'danger' : 'warning'}
        onConfirm={handleConfirmAction} onCancel={() => setConfirmAction(null)} />
    </div>
  );
};

export default OrdersPage;
