import { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  TextField,
  Button,
  Paper,
  Grid,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  IconButton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  LinearProgress,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Card,
  CardContent,
  CardActions,
  Divider,
  Tab,
  Tabs,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Switch,
  FormControlLabel,
  Snackbar,
  Badge,
  AppBar,
  Toolbar,
  Drawer,
  Fab,
  SpeedDial,
  SpeedDialAction,
  SpeedDialIcon,
  Stepper,
  Step,
  StepLabel,
  CircularProgress,
} from '@mui/material';
import {
  ExpandMore,
  Delete,
  Add,
  Save,
  Download,
  Preview,
  History,
  Help,
  Settings,
  DarkMode,
  LightMode,
  Article,
  Science,
  Business,
  School,
  ContentCopy,
  AutoAwesome,
  CheckCircle,
  Info,
  Warning,
  Error as ErrorIcon,
  Close,
  Edit,
  RestartAlt,
  Share,
  Print,
  FileDownload,
  CloudUpload,
  Bookmark,
  BookmarkBorder,
} from '@mui/icons-material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { toast, Toaster } from 'sonner';

// ========== CONFIGURACIÓN DE NORMAS ==========
const NORMAS_CONFIG = {
  apa7: { 
    nombre: 'APA 7ª Edición', 
    descripcion: 'American Psychological Association - Séptima Edición',
    color: '#1976d2'
  },
  apa6: { 
    nombre: 'APA 6ª Edición', 
    descripcion: 'American Psychological Association - Sexta Edición',
    color: '#1565c0'
  },
  icontec: { 
    nombre: 'ICONTEC', 
    descripcion: 'Instituto Colombiano de Normas Técnicas',
    color: '#388e3c'
  },
  vancouver: { 
    nombre: 'Vancouver', 
    descripcion: 'Estilo Vancouver para ciencias de la salud',
    color: '#d32f2f'
  },
  chicago: { 
    nombre: 'Chicago', 
    descripcion: 'Manual de Estilo Chicago',
    color: '#f57c00'
  },
  harvard: { 
    nombre: 'Harvard', 
    descripcion: 'Sistema de Referenciación Harvard',
    color: '#7b1fa2'
  },
  mla: { 
    nombre: 'MLA 9ª Edición', 
    descripcion: 'Modern Language Association',
    color: '#0288d1'
  },
  ieee: { 
    nombre: 'IEEE', 
    descripcion: 'Institute of Electrical and Electronics Engineers',
    color: '#5d4037'
  },
};

// ========== TIPOS DE INFORME ==========
const TIPOS_INFORME = {
  academico: {
    nombre: 'Académico General',
    icon: <Article />,
    color: '#1976d2',
    secciones: ['Introducción', 'Objetivos', 'Marco Teórico', 'Metodología', 'Desarrollo', 'Conclusiones', 'Recomendaciones', 'Referencias']
  },
  laboratorio: {
    nombre: 'Laboratorio',
    icon: <Science />,
    color: '#9c27b0',
    secciones: ['Introducción', 'Materiales', 'Procedimiento', 'Resultados', 'Discusión', 'Conclusiones', 'Recomendaciones', 'Referencias']
  },
  empresarial: {
    nombre: 'Empresarial/Ejecutivo',
    icon: <Business />,
    color: '#f57c00',
    secciones: ['Resumen Ejecutivo', 'Introducción', 'Análisis', 'Oportunidades', 'Recomendaciones', 'Conclusiones', 'Referencias']
  },
  tesis: {
    nombre: 'Tesis/Monografía',
    icon: <School />,
    color: '#388e3c',
    secciones: ['Resumen', 'Introducción', 'Planteamiento', 'Objetivos', 'Hipótesis', 'Marco Teórico', 'Metodología', 'Resultados', 'Conclusiones', 'Referencias']
  },
};

// ========== PLANTILLAS PREDEFINIDAS ==========
const PLANTILLAS = [
  {
    id: 'educacion',
    nombre: 'Educación y Pedagogía',
    tema: 'Metodologías de enseñanza innovadoras en el siglo XXI',
    tipo: 'academico',
    norma: 'apa7'
  },
  {
    id: 'ciencias',
    nombre: 'Ciencias Experimentales',
    tema: 'Análisis de compuestos químicos orgánicos',
    tipo: 'laboratorio',
    norma: 'vancouver'
  },
  {
    id: 'negocios',
    nombre: 'Análisis de Negocios',
    tema: 'Plan estratégico de marketing digital',
    tipo: 'empresarial',
    norma: 'apa7'
  },
  {
    id: 'investigacion',
    nombre: 'Investigación Avanzada',
    tema: 'Impacto de la tecnología en la sociedad moderna',
    tipo: 'tesis',
    norma: 'apa7'
  },
];

interface FormData {
  nombre: string;
  otros_autores: string[];
  tema: string;
  asignatura: string;
  profesor: string;
  institucion: string;
  fecha_entrega: string;
  tipo_informe: keyof typeof TIPOS_INFORME;
  norma: keyof typeof NORMAS_CONFIG;
  texto_completo: string;
}

interface HistorialItem {
  id: string;
  fecha: string;
  tema: string;
  tipo: string;
  norma: string;
}

export default function App() {
  // ========== ESTADOS ==========
  const [formData, setFormData] = useState<FormData>({
    nombre: '',
    otros_autores: [],
    tema: '',
    asignatura: '',
    profesor: '',
    institucion: '',
    fecha_entrega: new Date().toISOString().split('T')[0],
    tipo_informe: 'academico',
    norma: 'apa7',
    texto_completo: '',
  });

  const [nuevoAutor, setNuevoAutor] = useState('');
  const [loading, setLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [tabValue, setTabValue] = useState(0);
  const [historial, setHistorial] = useState<HistorialItem[]>([]);
  const [openPreview, setOpenPreview] = useState(false);
  const [openHistory, setOpenHistory] = useState(false);
  const [openHelp, setOpenHelp] = useState(false);
  const [openTemplates, setOpenTemplates] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [savedDrafts, setSavedDrafts] = useState<any[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [wordCount, setWordCount] = useState(0);
  const [charCount, setCharCount] = useState(0);
  const [bookmark, setBookmark] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  // ========== TEMA MUI ==========
  const theme = createTheme({
    palette: {
      mode: darkMode ? 'dark' : 'light',
      primary: {
        main: '#1976d2',
      },
      secondary: {
        main: '#dc004e',
      },
    },
    typography: {
      fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    },
    components: {
      MuiButton: {
        styleOverrides: {
          root: {
            textTransform: 'none',
            borderRadius: 8,
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            borderRadius: 12,
          },
        },
      },
    },
  });

  // ========== EFECTOS ==========
  useEffect(() => {
    // Cargar datos guardados
    const savedData = localStorage.getItem('academicReportDraft');
    if (savedData) {
      try {
        const parsed = JSON.parse(savedData);
        setFormData(parsed);
        toast.success('Borrador recuperado');
      } catch (e) {
        console.error('Error al cargar borrador:', e);
      }
    }

    // Cargar historial
    const savedHistory = localStorage.getItem('reportHistory');
    if (savedHistory) {
      try {
        setHistorial(JSON.parse(savedHistory));
      } catch (e) {
        console.error('Error al cargar historial:', e);
      }
    }

    // Cargar borradores
    const drafts = localStorage.getItem('savedDrafts');
    if (drafts) {
      try {
        setSavedDrafts(JSON.parse(drafts));
      } catch (e) {
        console.error('Error al cargar borradores:', e);
      }
    }
  }, []);

  useEffect(() => {
    // Calcular palabras y caracteres
    const text = formData.texto_completo;
    setCharCount(text.length);
    setWordCount(text.trim() ? text.trim().split(/\s+/).length : 0);
  }, [formData.texto_completo]);

  // ========== MANEJADORES ==========
  const handleInputChange = (field: keyof FormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const agregarAutor = () => {
    if (nuevoAutor.trim() && !formData.otros_autores.includes(nuevoAutor.trim())) {
      setFormData(prev => ({
        ...prev,
        otros_autores: [...prev.otros_autores, nuevoAutor.trim()]
      }));
      setNuevoAutor('');
      toast.success('Autor agregado');
    }
  };

  const eliminarAutor = (autor: string) => {
    setFormData(prev => ({
      ...prev,
      otros_autores: prev.otros_autores.filter(a => a !== autor)
    }));
    toast.info('Autor eliminado');
  };

  const guardarBorrador = () => {
    try {
      localStorage.setItem('academicReportDraft', JSON.stringify(formData));
      
      // Guardar en lista de borradores
      const newDraft = {
        id: Date.now().toString(),
        fecha: new Date().toLocaleString(),
        tema: formData.tema || 'Sin título',
        tipo: formData.tipo_informe,
        data: formData
      };
      
      const updatedDrafts = [newDraft, ...savedDrafts].slice(0, 10); // Máximo 10 borradores
      setSavedDrafts(updatedDrafts);
      localStorage.setItem('savedDrafts', JSON.stringify(updatedDrafts));
      
      toast.success('Borrador guardado exitosamente');
    } catch (error) {
      toast.error('Error al guardar borrador');
    }
  };

  const cargarBorrador = (draft: any) => {
    setFormData(draft.data);
    setDrawerOpen(false);
    toast.success('Borrador cargado');
  };

  const limpiarFormulario = () => {
    const confirmReset = window.confirm('¿Estás seguro de que deseas limpiar todos los campos?');
    if (confirmReset) {
      setFormData({
        nombre: '',
        otros_autores: [],
        tema: '',
        asignatura: '',
        profesor: '',
        institucion: '',
        fecha_entrega: new Date().toISOString().split('T')[0],
        tipo_informe: 'academico',
        norma: 'apa7',
        texto_completo: '',
      });
      setActiveStep(0);
      toast.info('Formulario limpiado');
    }
  };

  const aplicarPlantilla = (plantilla: any) => {
    setFormData(prev => ({
      ...prev,
      tema: plantilla.tema,
      tipo_informe: plantilla.tipo,
      norma: plantilla.norma,
    }));
    setOpenTemplates(false);
    toast.success(`Plantilla "${plantilla.nombre}" aplicada`);
  };

  const validarFormulario = (): boolean => {
    if (!formData.nombre.trim()) {
      toast.error('Por favor ingresa tu nombre');
      return false;
    }
    if (!formData.tema.trim() || formData.tema.length < 5) {
      toast.error('El tema debe tener al menos 5 caracteres');
      return false;
    }
    if (!formData.asignatura.trim()) {
      toast.error('Por favor ingresa la asignatura');
      return false;
    }
    if (!formData.institucion.trim()) {
      toast.error('Por favor ingresa la institución');
      return false;
    }
    return true;
  };

  const generarInforme = async () => {
    if (!validarFormulario()) return;

    setLoading(true);
    toast.loading('Generando informe...', { id: 'generating' });

    try {
      // Simulación de generación (en producción conectarías con tu backend)
      await new Promise(resolve => setTimeout(resolve, 3000));

      // Agregar al historial
      const nuevoItem: HistorialItem = {
        id: Date.now().toString(),
        fecha: new Date().toLocaleString(),
        tema: formData.tema,
        tipo: TIPOS_INFORME[formData.tipo_informe].nombre,
        norma: NORMAS_CONFIG[formData.norma].nombre,
      };

      const nuevoHistorial = [nuevoItem, ...historial].slice(0, 20);
      setHistorial(nuevoHistorial);
      localStorage.setItem('reportHistory', JSON.stringify(nuevoHistorial));

      toast.success('¡Informe generado exitosamente!', { id: 'generating' });
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 5000);

      // Aquí simularíamos la descarga del PDF
      toast.info('Descarga iniciada...');

    } catch (error) {
      toast.error('Error al generar el informe', { id: 'generating' });
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const steps = ['Información Personal', 'Detalles del Informe', 'Contenido Adicional', 'Revisión'];

  // ========== RENDERIZADO ==========
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Toaster position="top-right" richColors expand={true} />
      
      <Box sx={{ flexGrow: 1, minHeight: '100vh', backgroundColor: darkMode ? '#121212' : '#f5f5f5' }}>
        {/* AppBar */}
        <AppBar position="sticky" elevation={2}>
          <Toolbar>
            <Article sx={{ mr: 2 }} />
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              Academic Report Pro
            </Typography>
            
            <Tooltip title="Plantillas">
              <IconButton color="inherit" onClick={() => setOpenTemplates(true)}>
                <Badge badgeContent={PLANTILLAS.length} color="error">
                  <ContentCopy />
                </Badge>
              </IconButton>
            </Tooltip>

            <Tooltip title="Historial">
              <IconButton color="inherit" onClick={() => setOpenHistory(true)}>
                <Badge badgeContent={historial.length} color="error">
                  <History />
                </Badge>
              </IconButton>
            </Tooltip>

            <Tooltip title="Borradores">
              <IconButton color="inherit" onClick={() => setDrawerOpen(true)}>
                <Badge badgeContent={savedDrafts.length} color="error">
                  <Save />
                </Badge>
              </IconButton>
            </Tooltip>

            <Tooltip title="Ayuda">
              <IconButton color="inherit" onClick={() => setOpenHelp(true)}>
                <Help />
              </IconButton>
            </Tooltip>

            <Tooltip title={darkMode ? "Modo Claro" : "Modo Oscuro"}>
              <IconButton color="inherit" onClick={() => setDarkMode(!darkMode)}>
                {darkMode ? <LightMode /> : <DarkMode />}
              </IconButton>
            </Tooltip>
          </Toolbar>
        </AppBar>

        {/* Progreso de carga */}
        {loading && <LinearProgress />}

        {/* Contenido Principal */}
        <Container maxWidth="lg" sx={{ py: 4 }}>
          {/* Alert de éxito */}
          {showSuccess && (
            <Alert 
              severity="success" 
              icon={<CheckCircle />}
              sx={{ mb: 3 }}
              onClose={() => setShowSuccess(false)}
            >
              <Typography variant="h6">¡Informe generado exitosamente!</Typography>
              <Typography>Tu informe académico ha sido creado y está listo para descargar.</Typography>
            </Alert>
          )}

          {/* Stepper */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Stepper activeStep={activeStep} alternativeLabel>
              {steps.map((label) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>
          </Paper>

          {/* Formulario Principal */}
          <Paper elevation={3} sx={{ p: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h4" gutterBottom>
                Generador de Informes Académicos
              </Typography>
              <Tooltip title={bookmark ? "Marcado" : "Marcar como importante"}>
                <IconButton onClick={() => setBookmark(!bookmark)} color={bookmark ? "primary" : "default"}>
                  {bookmark ? <Bookmark /> : <BookmarkBorder />}
                </IconButton>
              </Tooltip>
            </Box>

            <Divider sx={{ mb: 3 }} />

            {/* Tabs */}
            <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)} sx={{ mb: 3 }}>
              <Tab label="Información Básica" />
              <Tab label="Configuración Avanzada" />
              <Tab label="Contenido" />
            </Tabs>

            {/* Tab 1: Información Básica */}
            {tabValue === 0 && (
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    required
                    label="Nombre del Autor Principal"
                    value={formData.nombre}
                    onChange={(e) => handleInputChange('nombre', e.target.value)}
                    placeholder="Ej: Juan Pérez"
                    helperText="Ingresa tu nombre completo"
                    InputProps={{
                      startAdornment: <Edit sx={{ mr: 1, color: 'action.active' }} />
                    }}
                  />
                </Grid>

                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    required
                    label="Tema del Informe"
                    value={formData.tema}
                    onChange={(e) => handleInputChange('tema', e.target.value)}
                    placeholder="Ej: Análisis de metodologías educativas"
                    helperText={`${formData.tema.length} caracteres`}
                    InputProps={{
                      startAdornment: <Article sx={{ mr: 1, color: 'action.active' }} />
                    }}
                  />
                </Grid>

                <Grid item xs={12}>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
                    <TextField
                      fullWidth
                      label="Agregar Co-autores"
                      value={nuevoAutor}
                      onChange={(e) => setNuevoAutor(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && agregarAutor()}
                      placeholder="Presiona Enter para agregar"
                    />
                    <Button 
                      variant="contained" 
                      startIcon={<Add />} 
                      onClick={agregarAutor}
                      sx={{ height: 56 }}
                    >
                      Agregar
                    </Button>
                  </Box>
                  
                  {formData.otros_autores.length > 0 && (
                    <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {formData.otros_autores.map((autor) => (
                        <Chip
                          key={autor}
                          label={autor}
                          onDelete={() => eliminarAutor(autor)}
                          color="primary"
                          variant="outlined"
                        />
                      ))}
                    </Box>
                  )}
                </Grid>

                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    required
                    label="Asignatura"
                    value={formData.asignatura}
                    onChange={(e) => handleInputChange('asignatura', e.target.value)}
                    placeholder="Ej: Metodología de la Investigación"
                  />
                </Grid>

                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Profesor/Docente"
                    value={formData.profesor}
                    onChange={(e) => handleInputChange('profesor', e.target.value)}
                    placeholder="Ej: Dr. Carlos García"
                  />
                </Grid>

                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    required
                    label="Institución Educativa"
                    value={formData.institucion}
                    onChange={(e) => handleInputChange('institucion', e.target.value)}
                    placeholder="Ej: Universidad Nacional"
                  />
                </Grid>

                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    type="date"
                    label="Fecha de Entrega"
                    value={formData.fecha_entrega}
                    onChange={(e) => handleInputChange('fecha_entrega', e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
              </Grid>
            )}

            {/* Tab 2: Configuración Avanzada */}
            {tabValue === 1 && (
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom>
                    Tipo de Informe
                  </Typography>
                  <Grid container spacing={2}>
                    {Object.entries(TIPOS_INFORME).map(([key, tipo]) => (
                      <Grid item xs={12} sm={6} md={3} key={key}>
                        <Card 
                          sx={{ 
                            cursor: 'pointer',
                            border: formData.tipo_informe === key ? `2px solid ${tipo.color}` : '1px solid #e0e0e0',
                            transition: 'all 0.3s',
                            '&:hover': {
                              transform: 'translateY(-4px)',
                              boxShadow: 4,
                            }
                          }}
                          onClick={() => handleInputChange('tipo_informe', key)}
                        >
                          <CardContent sx={{ textAlign: 'center' }}>
                            <Box sx={{ color: tipo.color, mb: 1 }}>
                              {tipo.icon}
                            </Box>
                            <Typography variant="subtitle2">
                              {tipo.nombre}
                            </Typography>
                            {formData.tipo_informe === key && (
                              <CheckCircle sx={{ color: tipo.color, mt: 1 }} />
                            )}
                          </CardContent>
                        </Card>
                      </Grid>
                    ))}
                  </Grid>
                </Grid>

                <Grid item xs={12}>
                  <Divider sx={{ my: 2 }} />
                </Grid>

                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom>
                    Norma Académica
                  </Typography>
                  <FormControl fullWidth>
                    <InputLabel>Seleccionar Norma</InputLabel>
                    <Select
                      value={formData.norma}
                      onChange={(e) => handleInputChange('norma', e.target.value)}
                      label="Seleccionar Norma"
                    >
                      {Object.entries(NORMAS_CONFIG).map(([key, norma]) => (
                        <MenuItem key={key} value={key}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                            <Box 
                              sx={{ 
                                width: 12, 
                                height: 12, 
                                borderRadius: '50%', 
                                backgroundColor: norma.color 
                              }} 
                            />
                            <Box>
                              <Typography variant="body1">{norma.nombre}</Typography>
                              <Typography variant="caption" color="text.secondary">
                                {norma.descripcion}
                              </Typography>
                            </Box>
                          </Box>
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12}>
                  <Alert severity="info" icon={<Info />}>
                    <Typography variant="body2">
                      <strong>Secciones incluidas en {TIPOS_INFORME[formData.tipo_informe].nombre}:</strong>
                    </Typography>
                    <Box component="ul" sx={{ mt: 1, pl: 2 }}>
                      {TIPOS_INFORME[formData.tipo_informe].secciones.map((seccion) => (
                        <li key={seccion}>{seccion}</li>
                      ))}
                    </Box>
                  </Alert>
                </Grid>
              </Grid>
            )}

            {/* Tab 3: Contenido */}
            {tabValue === 2 && (
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6">
                      Información Adicional (Opcional)
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 2 }}>
                      <Chip 
                        icon={<Article />} 
                        label={`${wordCount} palabras`} 
                        color="primary" 
                        variant="outlined" 
                      />
                      <Chip 
                        icon={<Article />} 
                        label={`${charCount} caracteres`} 
                        color="secondary" 
                        variant="outlined" 
                      />
                    </Box>
                  </Box>
                  
                  <TextField
                    fullWidth
                    multiline
                    rows={12}
                    value={formData.texto_completo}
                    onChange={(e) => handleInputChange('texto_completo', e.target.value)}
                    placeholder="Aquí puedes agregar contexto adicional, datos específicos, resultados previos, o cualquier información que ayude a generar un informe más preciso y personalizado..."
                    variant="outlined"
                    helperText="Esta información será utilizada por la IA para generar un contenido más específico y relevante"
                  />
                </Grid>

                <Grid item xs={12}>
                  <Alert severity="success" icon={<AutoAwesome />}>
                    <Typography variant="body2">
                      <strong>Consejo:</strong> Mientras más detalles proporciones, más personalizado y específico será tu informe. 
                      Incluye datos, estadísticas, observaciones o cualquier información relevante.
                    </Typography>
                  </Alert>
                </Grid>
              </Grid>
            )}

            <Divider sx={{ my: 4 }} />

            {/* Botones de Acción */}
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', justifyContent: 'space-between' }}>
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                <Button
                  variant="outlined"
                  startIcon={<RestartAlt />}
                  onClick={limpiarFormulario}
                  color="error"
                >
                  Limpiar
                </Button>

                <Button
                  variant="outlined"
                  startIcon={<Save />}
                  onClick={guardarBorrador}
                  color="info"
                >
                  Guardar Borrador
                </Button>

                <Button
                  variant="outlined"
                  startIcon={<Preview />}
                  onClick={() => setOpenPreview(true)}
                >
                  Vista Previa
                </Button>
              </Box>

              <Button
                variant="contained"
                size="large"
                startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <Download />}
                onClick={generarInforme}
                disabled={loading}
                sx={{ 
                  minWidth: 200,
                  background: 'linear-gradient(45deg, #1976d2 30%, #42a5f5 90%)',
                  boxShadow: '0 3px 5px 2px rgba(25, 118, 210, .3)',
                }}
              >
                {loading ? 'Generando...' : 'Generar Informe PDF'}
              </Button>
            </Box>

            {/* Navegación de Stepper */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
              <Button
                disabled={activeStep === 0}
                onClick={() => setActiveStep(prev => prev - 1)}
              >
                Anterior
              </Button>
              <Button
                variant="contained"
                onClick={() => activeStep < steps.length - 1 ? setActiveStep(prev => prev + 1) : generarInforme()}
              >
                {activeStep === steps.length - 1 ? 'Finalizar' : 'Siguiente'}
              </Button>
            </Box>
          </Paper>

          {/* Información Adicional */}
          <Grid container spacing={3} sx={{ mt: 2 }}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <CheckCircle sx={{ color: 'success.main', mr: 1 }} />
                    <Typography variant="h6">Profesional</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    Informes generados con estándares académicos internacionales y formato profesional.
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <AutoAwesome sx={{ color: 'primary.main', mr: 1 }} />
                    <Typography variant="h6">IA Avanzada</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    Contenido generado con inteligencia artificial de última generación para resultados óptimos.
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <School sx={{ color: 'secondary.main', mr: 1 }} />
                    <Typography variant="h6">8 Normas</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    Soporte completo para APA, IEEE, MLA, Vancouver, Chicago, Harvard, ICONTEC y más.
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Container>

        {/* Dialog: Vista Previa */}
        <Dialog open={openPreview} onClose={() => setOpenPreview(false)} maxWidth="md" fullWidth>
          <DialogTitle>
            Vista Previa del Informe
            <IconButton
              onClick={() => setOpenPreview(false)}
              sx={{ position: 'absolute', right: 8, top: 8 }}
            >
              <Close />
            </IconButton>
          </DialogTitle>
          <DialogContent dividers>
            <Typography variant="h6" gutterBottom>Portada</Typography>
            <Paper sx={{ p: 3, mb: 2, backgroundColor: 'grey.100' }}>
              <Typography variant="h4" align="center" gutterBottom>
                INFORME ACADÉMICO
              </Typography>
              <Typography align="center" gutterBottom sx={{ mt: 3 }}>
                <strong>{formData.tema || 'Tema del Informe'}</strong>
              </Typography>
              <Typography align="center" sx={{ mt: 4 }}>
                <strong>Presentado por:</strong> {formData.nombre || 'Nombre del Autor'}
              </Typography>
              {formData.otros_autores.length > 0 && (
                <Typography align="center">
                  <strong>Con la participación de:</strong> {formData.otros_autores.join(', ')}
                </Typography>
              )}
              <Typography align="center">
                <strong>Asignatura:</strong> {formData.asignatura || 'Asignatura'}
              </Typography>
              <Typography align="center">
                <strong>Docente:</strong> {formData.profesor || 'Docente'}
              </Typography>
              <Typography align="center">
                <strong>Institución:</strong> {formData.institucion || 'Institución'}
              </Typography>
              <Typography align="center" sx={{ mt: 2 }}>
                <strong>Fecha:</strong> {formData.fecha_entrega}
              </Typography>
            </Paper>

            <Typography variant="h6" gutterBottom>Configuración</Typography>
            <List>
              <ListItem>
                <ListItemIcon>
                  {TIPOS_INFORME[formData.tipo_informe].icon}
                </ListItemIcon>
                <ListItemText 
                  primary="Tipo de Informe"
                  secondary={TIPOS_INFORME[formData.tipo_informe].nombre}
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <Article />
                </ListItemIcon>
                <ListItemText 
                  primary="Norma Académica"
                  secondary={NORMAS_CONFIG[formData.norma].nombre}
                />
              </ListItem>
            </List>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpenPreview(false)}>Cerrar</Button>
            <Button variant="contained" onClick={generarInforme}>
              Generar Ahora
            </Button>
          </DialogActions>
        </Dialog>

        {/* Dialog: Historial */}
        <Dialog open={openHistory} onClose={() => setOpenHistory(false)} maxWidth="md" fullWidth>
          <DialogTitle>
            Historial de Informes Generados
            <IconButton
              onClick={() => setOpenHistory(false)}
              sx={{ position: 'absolute', right: 8, top: 8 }}
            >
              <Close />
            </IconButton>
          </DialogTitle>
          <DialogContent dividers>
            {historial.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <History sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6" color="text.secondary">
                  No hay informes en el historial
                </Typography>
                <Typography color="text.secondary">
                  Los informes generados aparecerán aquí
                </Typography>
              </Box>
            ) : (
              <List>
                {historial.map((item, index) => (
                  <ListItem key={item.id} divider={index < historial.length - 1}>
                    <ListItemIcon>
                      <Article />
                    </ListItemIcon>
                    <ListItemText
                      primary={item.tema}
                      secondary={
                        <>
                          <Typography component="span" variant="body2" color="text.primary">
                            {item.tipo}
                          </Typography>
                          {` — ${item.norma} — ${item.fecha}`}
                        </>
                      }
                    />
                    <IconButton size="small">
                      <Download />
                    </IconButton>
                  </ListItem>
                ))}
              </List>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpenHistory(false)}>Cerrar</Button>
          </DialogActions>
        </Dialog>

        {/* Dialog: Ayuda */}
        <Dialog open={openHelp} onClose={() => setOpenHelp(false)} maxWidth="md" fullWidth>
          <DialogTitle>
            Centro de Ayuda
            <IconButton
              onClick={() => setOpenHelp(false)}
              sx={{ position: 'absolute', right: 8, top: 8 }}
            >
              <Close />
            </IconButton>
          </DialogTitle>
          <DialogContent dividers>
            <Typography variant="h6" gutterBottom>
              ¿Cómo usar Academic Report Pro?
            </Typography>
            
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography>1. Completar Información Básica</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Typography>
                  Ingresa tu nombre, el tema del informe, asignatura, institución y fecha de entrega. 
                  Puedes agregar co-autores si es un trabajo en equipo.
                </Typography>
              </AccordionDetails>
            </Accordion>

            <Accordion>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography>2. Seleccionar Tipo y Norma</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Typography>
                  Elige el tipo de informe (Académico, Laboratorio, Empresarial o Tesis) y la norma 
                  académica que prefieras (APA, IEEE, MLA, etc.).
                </Typography>
              </AccordionDetails>
            </Accordion>

            <Accordion>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography>3. Agregar Contenido Opcional</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Typography>
                  Proporciona información adicional para que la IA genere un contenido más específico 
                  y personalizado. Incluye datos, observaciones o contexto relevante.
                </Typography>
              </AccordionDetails>
            </Accordion>

            <Accordion>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography>4. Generar y Descargar</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Typography>
                  Haz clic en "Generar Informe PDF" y espera unos segundos. El sistema creará tu 
                  informe profesional que podrás descargar inmediatamente.
                </Typography>
              </AccordionDetails>
            </Accordion>

            <Box sx={{ mt: 3, p: 2, backgroundColor: 'info.light', borderRadius: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                💡 Consejos Útiles:
              </Typography>
              <Typography variant="body2">
                • Guarda borradores mientras trabajas
                <br />
                • Usa plantillas predefinidas para comenzar rápido
                <br />
                • Revisa la vista previa antes de generar
                <br />
                • Cuanta más información proporciones, mejor será el resultado
              </Typography>
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpenHelp(false)}>Entendido</Button>
          </DialogActions>
        </Dialog>

        {/* Dialog: Plantillas */}
        <Dialog open={openTemplates} onClose={() => setOpenTemplates(false)} maxWidth="md" fullWidth>
          <DialogTitle>
            Plantillas Predefinidas
            <IconButton
              onClick={() => setOpenTemplates(false)}
              sx={{ position: 'absolute', right: 8, top: 8 }}
            >
              <Close />
            </IconButton>
          </DialogTitle>
          <DialogContent dividers>
            <Grid container spacing={2}>
              {PLANTILLAS.map((plantilla) => (
                <Grid item xs={12} sm={6} key={plantilla.id}>
                  <Card 
                    sx={{ 
                      cursor: 'pointer',
                      transition: 'all 0.3s',
                      '&:hover': {
                        transform: 'scale(1.02)',
                        boxShadow: 4,
                      }
                    }}
                  >
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        {plantilla.nombre}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        {plantilla.tema}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                        <Chip label={TIPOS_INFORME[plantilla.tipo as keyof typeof TIPOS_INFORME].nombre} size="small" />
                        <Chip label={NORMAS_CONFIG[plantilla.norma as keyof typeof NORMAS_CONFIG].nombre} size="small" color="primary" />
                      </Box>
                    </CardContent>
                    <CardActions>
                      <Button 
                        size="small" 
                        fullWidth 
                        variant="contained"
                        onClick={() => aplicarPlantilla(plantilla)}
                      >
                        Usar Plantilla
                      </Button>
                    </CardActions>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpenTemplates(false)}>Cerrar</Button>
          </DialogActions>
        </Dialog>

        {/* Drawer: Borradores */}
        <Drawer
          anchor="right"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
        >
          <Box sx={{ width: 350, p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Borradores Guardados</Typography>
              <IconButton onClick={() => setDrawerOpen(false)}>
                <Close />
              </IconButton>
            </Box>
            <Divider sx={{ mb: 2 }} />
            
            {savedDrafts.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Save sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                <Typography variant="body2" color="text.secondary">
                  No hay borradores guardados
                </Typography>
              </Box>
            ) : (
              <List>
                {savedDrafts.map((draft, index) => (
                  <ListItem 
                    key={draft.id}
                    divider={index < savedDrafts.length - 1}
                    sx={{ 
                      cursor: 'pointer',
                      '&:hover': { backgroundColor: 'action.hover' }
                    }}
                    onClick={() => cargarBorrador(draft)}
                  >
                    <ListItemIcon>
                      <Article />
                    </ListItemIcon>
                    <ListItemText
                      primary={draft.tema}
                      secondary={draft.fecha}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Box>
        </Drawer>

        {/* FAB de Acciones Rápidas */}
        <SpeedDial
          ariaLabel="Acciones rápidas"
          sx={{ position: 'fixed', bottom: 16, right: 16 }}
          icon={<SpeedDialIcon />}
        >
          <SpeedDialAction
            icon={<Save />}
            tooltipTitle="Guardar Borrador"
            onClick={guardarBorrador}
          />
          <SpeedDialAction
            icon={<Preview />}
            tooltipTitle="Vista Previa"
            onClick={() => setOpenPreview(true)}
          />
          <SpeedDialAction
            icon={<Download />}
            tooltipTitle="Generar PDF"
            onClick={generarInforme}
          />
          <SpeedDialAction
            icon={<RestartAlt />}
            tooltipTitle="Limpiar"
            onClick={limpiarFormulario}
          />
        </SpeedDial>
      </Box>
    </ThemeProvider>
  );
}
