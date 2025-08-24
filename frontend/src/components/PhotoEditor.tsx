import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { PrepareResponse, SelectionArea, GenerateResponse } from '../types';
import { apiService } from '../services/api';

interface PhotoEditorProps {
  prepareData: PrepareResponse;
  onPhotoGenerated: (result: GenerateResponse) => void;
  onBack: () => void;
}

const PhotoEditor: React.FC<PhotoEditorProps> = ({ prepareData, onPhotoGenerated, onBack }) => {
  const { t } = useTranslation();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [selection, setSelection] = useState<SelectionArea>(prepareData.default_selection);
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [resizeHandle, setResizeHandle] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [canvasScale, setCanvasScale] = useState(1);
  const [canvasOffset, setCanvasOffset] = useState({ x: 0, y: 0 });

  const imageRef = useRef<HTMLImageElement>(new Image());

  useEffect(() => {
    const image = imageRef.current;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    image.onload = () => {
      // Calculate scale to fit image in canvas while maintaining aspect ratio
      const maxWidth = 800;
      const maxHeight = 600;
      const imageAspectRatio = image.width / image.height;
      const maxAspectRatio = maxWidth / maxHeight;

      let displayWidth = maxWidth;
      let displayHeight = maxHeight;

      if (imageAspectRatio > maxAspectRatio) {
        displayHeight = displayWidth / imageAspectRatio;
      } else {
        displayWidth = displayHeight * imageAspectRatio;
      }

      canvas.width = displayWidth;
      canvas.height = displayHeight;

      const scale = displayWidth / image.width;
      setCanvasScale(scale);
      setCanvasOffset({ x: 0, y: 0 });

      drawCanvas();
    };

    const imageData = `data:image/${prepareData.image_format.toLowerCase()};base64,${prepareData.image_data}`;
    image.src = imageData;
  }, [prepareData]);

  const drawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const image = imageRef.current;
    if (!canvas || !image.complete) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw background image
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);

    // Draw semi-transparent overlay
    ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Clear selection area to show original image
    const scaledSelection = {
      x: selection.x * canvasScale,
      y: selection.y * canvasScale,
      width: selection.width * canvasScale,
      height: selection.height * canvasScale,
    };

    ctx.clearRect(scaledSelection.x, scaledSelection.y, scaledSelection.width, scaledSelection.height);
    ctx.drawImage(
      image,
      selection.x, selection.y, selection.width, selection.height,
      scaledSelection.x, scaledSelection.y, scaledSelection.width, scaledSelection.height
    );

    // Draw selection border
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.strokeRect(scaledSelection.x, scaledSelection.y, scaledSelection.width, scaledSelection.height);

    // Draw resize handles
    const handleSize = 8;
    ctx.fillStyle = '#3b82f6';
    ctx.setLineDash([]);

    const handles = [
      { x: scaledSelection.x - handleSize / 2, y: scaledSelection.y - handleSize / 2, cursor: 'nw-resize' },
      { x: scaledSelection.x + scaledSelection.width - handleSize / 2, y: scaledSelection.y - handleSize / 2, cursor: 'ne-resize' },
      { x: scaledSelection.x - handleSize / 2, y: scaledSelection.y + scaledSelection.height - handleSize / 2, cursor: 'sw-resize' },
      { x: scaledSelection.x + scaledSelection.width - handleSize / 2, y: scaledSelection.y + scaledSelection.height - handleSize / 2, cursor: 'se-resize' },
    ];

    handles.forEach(handle => {
      ctx.fillRect(handle.x, handle.y, handleSize, handleSize);
    });
  }, [selection, canvasScale]);

  useEffect(() => {
    drawCanvas();
  }, [drawCanvas]);

  const getMousePosition = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };

    const rect = canvas.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) / canvasScale,
      y: (e.clientY - rect.top) / canvasScale,
    };
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const scaledSelection = {
      x: selection.x * canvasScale,
      y: selection.y * canvasScale,
      width: selection.width * canvasScale,
      height: selection.height * canvasScale,
    };

    // Check if clicking on resize handles
    const handleSize = 8;
    const handles = [
      { x: scaledSelection.x - handleSize / 2, y: scaledSelection.y - handleSize / 2, type: 'nw' },
      { x: scaledSelection.x + scaledSelection.width - handleSize / 2, y: scaledSelection.y - handleSize / 2, type: 'ne' },
      { x: scaledSelection.x - handleSize / 2, y: scaledSelection.y + scaledSelection.height - handleSize / 2, type: 'sw' },
      { x: scaledSelection.x + scaledSelection.width - handleSize / 2, y: scaledSelection.y + scaledSelection.height - handleSize / 2, type: 'se' },
    ];

    for (const handle of handles) {
      if (x >= handle.x && x <= handle.x + handleSize && y >= handle.y && y <= handle.y + handleSize) {
        setIsResizing(true);
        setResizeHandle(handle.type);
        setDragStart({ x, y });
        return;
      }
    }

    // Check if clicking inside selection area for dragging
    if (x >= scaledSelection.x && x <= scaledSelection.x + scaledSelection.width &&
        y >= scaledSelection.y && y <= scaledSelection.y + scaledSelection.height) {
      setIsDragging(true);
      setDragStart({ x, y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (isDragging) {
      const deltaX = (x - dragStart.x) / canvasScale;
      const deltaY = (y - dragStart.y) / canvasScale;

      const newSelection = {
        ...selection,
        x: Math.max(0, Math.min(prepareData.image_dimensions.width - selection.width, selection.x + deltaX)),
        y: Math.max(0, Math.min(prepareData.image_dimensions.height - selection.height, selection.y + deltaY)),
      };

      setSelection(newSelection);
      setDragStart({ x, y });
    } else if (isResizing && resizeHandle) {
      const deltaX = (x - dragStart.x) / canvasScale;
      const deltaY = (y - dragStart.y) / canvasScale;

      let newSelection = { ...selection };

      switch (resizeHandle) {
        case 'nw':
          newSelection.x += deltaX;
          newSelection.y += deltaY;
          newSelection.width -= deltaX;
          newSelection.height -= deltaY;
          break;
        case 'ne':
          newSelection.y += deltaY;
          newSelection.width += deltaX;
          newSelection.height -= deltaY;
          break;
        case 'sw':
          newSelection.x += deltaX;
          newSelection.width -= deltaX;
          newSelection.height += deltaY;
          break;
        case 'se':
          newSelection.width += deltaX;
          newSelection.height += deltaY;
          break;
      }

      // Maintain aspect ratio
      const targetAspectRatio = prepareData.target_dimensions.width / prepareData.target_dimensions.height;
      
      if (newSelection.width / newSelection.height > targetAspectRatio) {
        newSelection.width = newSelection.height * targetAspectRatio;
      } else {
        newSelection.height = newSelection.width / targetAspectRatio;
      }

      // Ensure selection stays within bounds
      newSelection.x = Math.max(0, Math.min(prepareData.image_dimensions.width - newSelection.width, newSelection.x));
      newSelection.y = Math.max(0, Math.min(prepareData.image_dimensions.height - newSelection.height, newSelection.y));
      newSelection.width = Math.max(50, Math.min(prepareData.image_dimensions.width - newSelection.x, newSelection.width));
      newSelection.height = Math.max(50, Math.min(prepareData.image_dimensions.height - newSelection.y, newSelection.height));

      setSelection(newSelection);
      setDragStart({ x, y });
    } else {
      // Update cursor based on hover position
      const scaledSelection = {
        x: selection.x * canvasScale,
        y: selection.y * canvasScale,
        width: selection.width * canvasScale,
        height: selection.height * canvasScale,
      };

      const handleSize = 8;
      const handles = [
        { x: scaledSelection.x - handleSize / 2, y: scaledSelection.y - handleSize / 2, cursor: 'nw-resize' },
        { x: scaledSelection.x + scaledSelection.width - handleSize / 2, y: scaledSelection.y - handleSize / 2, cursor: 'ne-resize' },
        { x: scaledSelection.x - handleSize / 2, y: scaledSelection.y + scaledSelection.height - handleSize / 2, cursor: 'sw-resize' },
        { x: scaledSelection.x + scaledSelection.width - handleSize / 2, y: scaledSelection.y + scaledSelection.height - handleSize / 2, cursor: 'se-resize' },
      ];

      let cursor = 'default';
      for (const handle of handles) {
        if (x >= handle.x && x <= handle.x + handleSize && y >= handle.y && y <= handle.y + handleSize) {
          cursor = handle.cursor;
          break;
        }
      }

      if (cursor === 'default' &&
          x >= scaledSelection.x && x <= scaledSelection.x + scaledSelection.width &&
          y >= scaledSelection.y && y <= scaledSelection.y + scaledSelection.height) {
        cursor = 'move';
      }

      canvas.style.cursor = cursor;
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setIsResizing(false);
    setResizeHandle(null);
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      const result = await apiService.generatePhoto(
        prepareData.image_data,
        selection,
        prepareData.country.id
      );
      onPhotoGenerated(result);
    } catch (error: any) {
      console.error('Generate error:', error);
      // Handle error (show to user)
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            {t('editor.title', 'Adjust Photo Area')}
          </h1>
          <p className="text-gray-600">
            {t('editor.subtitle', 'Drag and resize the rectangle to select the area for your passport photo')}
          </p>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex flex-col lg:flex-row gap-6">
            <div className="flex-1">
              <div className="mb-4">
                <p className="text-sm text-gray-600 mb-2">
                  {t('editor.instructions', 'Background removed automatically. Drag to move, resize from corners.')}
                </p>
                <div className="flex items-center gap-4 text-sm text-gray-500">
                  <span>Target: {prepareData.target_dimensions.width}×{prepareData.target_dimensions.height}px</span>
                  <span>Country: {prepareData.country.name}</span>
                </div>
              </div>
              
              <div className="border border-gray-300 rounded-lg overflow-hidden bg-gray-100 flex justify-center">
                <canvas
                  ref={canvasRef}
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onMouseLeave={handleMouseUp}
                  className="max-w-full h-auto cursor-crosshair"
                />
              </div>
            </div>

            <div className="lg:w-80">
              <div className="space-y-4">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-gray-900 mb-2">
                    {t('editor.selectionInfo', 'Selection Info')}
                  </h3>
                  <div className="space-y-2 text-sm text-gray-600">
                    <div>Position: {Math.round(selection.x)}, {Math.round(selection.y)}</div>
                    <div>Size: {Math.round(selection.width)} × {Math.round(selection.height)}px</div>
                    <div>Aspect Ratio: {(selection.width / selection.height).toFixed(2)}</div>
                  </div>
                </div>

                <div className="bg-blue-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-blue-900 mb-2">
                    {t('editor.tips', 'Tips')}
                  </h3>
                  <ul className="space-y-1 text-sm text-blue-700">
                    <li>• {t('editor.tip1', 'Drag inside rectangle to move')}</li>
                    <li>• {t('editor.tip2', 'Drag corners to resize')}</li>
                    <li>• {t('editor.tip3', 'Aspect ratio is maintained')}</li>
                    <li>• {t('editor.tip4', 'Face should be in upper portion')}</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 flex flex-col sm:flex-row gap-4 justify-between">
            <button
              onClick={onBack}
              className="px-6 py-3 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
              disabled={isGenerating}
            >
              {t('button.back', 'Back')}
            </button>

            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {isGenerating ? t('button.generating', 'Generating...') : t('button.generatePassportPhoto', 'Generate Passport Photo')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PhotoEditor;